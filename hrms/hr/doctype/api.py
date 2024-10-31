import cv2
import numpy as np
import base64
import face_recognition
from io import BytesIO
from PIL import Image
import os
import time
from datetime import datetime
from keras.models import load_model  # To load the spoof detection model
from frappe.utils import now_datetime
from keras.preprocessing.image import img_to_array

# Load the spoof detection model (replace 'path_to_model' with the actual path to your .h5 model)
spoof_model = load_model('path_to_your_trained_spoof_model.h5')

def capture_frames_for_recognition(camera_index=0, timeout=10, spoof_threshold=3, recognition_threshold=0.4):
    """
    Captures multiple frames for both spoof detection and face recognition.
    Stops when a recognized face is detected or the timeout is reached.
    
    Parameters:
    - camera_index: Index of the camera to use (default is 0).
    - timeout: Maximum time to capture frames (in seconds).
    - spoof_threshold: Number of consecutive frames that must pass the spoof detection.
    - recognition_threshold: The maximum face distance for recognition.
    """
    logger.info("Starting frame capture for spoof detection and face recognition")
    start_time = time.time()
    camera = cv2.VideoCapture(camera_index)
    
    spoof_frame_count = 0
    recognized_employee = None
    spoof_detected = False

    while True:
        # Capture frame-by-frame
        ret, frame = camera.read()
        if not ret:
            logger.error("Failed to capture frame")
            break

        # Save the frame as an image file
        frame_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        temp_image_path = "/tmp/frame_image.jpg"  # Temporary storage for processing
        frame_image.save(temp_image_path)

        # Perform spoof detection on this frame
        if detect_spoof(temp_image_path):
            # If spoof is detected, store the image and log the attempt
            spoof_detected = True
            save_spoof_image(temp_image_path)
            logger.warning("Spoof detected in the frame")
        else:
            spoof_frame_count += 1

        # Perform face recognition if the frame passed spoof detection
        if spoof_frame_count >= spoof_threshold:
            recognized_employee, message = checkin_user(temp_image_path, threshold=recognition_threshold)
            if recognized_employee:
                logger.info(f"Face recognized: {recognized_employee}")
                break  # Stop capturing frames once a face is recognized

        # Stop the process after the timeout
        if time.time() - start_time > timeout:
            logger.info("Timeout reached while capturing frames")
            break

    # Release the camera
    camera.release()
    cv2.destroyAllWindows()

    if recognized_employee:
        logger.info(f"Attendance marked for {recognized_employee}")
    elif spoof_detected:
        logger.warning("Spoofing was detected but no valid face was recognized")
    else:
        logger.error("No valid face recognized and no spoof detected")

def detect_spoof(image_path):
    """
    Detects whether the face in the given image is spoofed using the loaded .h5 model.
    Returns True if spoofing is detected, otherwise False.
    """
    logger.info(f"Starting spoof detection for image: {image_path}")

    # Load the image using OpenCV
    image = cv2.imread(image_path)
    
    # Preprocess the image for the model (adjust these steps based on how your model was trained)
    resized_image = cv2.resize(image, (224, 224))  # Resize the image to your model input size
    image_array = img_to_array(resized_image) / 255.0  # Convert to array and normalize
    image_array = np.expand_dims(image_array, axis=0)  # Add batch dimension

    # Perform spoof detection using the loaded model
    predictions = spoof_model.predict(image_array)
    
    # Assuming your model output is a probability (0 = real, 1 = spoof), adjust threshold accordingly
    spoof_detected = predictions[0][0] > 0.5  # If the output is > 0.5, consider it a spoof

    return spoof_detected

def checkin_user(image_path, threshold=0.4):
    """
    Performs face recognition on the given image and returns the employee ID if recognized.
    """
    try:
        logger.info(f"Starting face recognition for image: {image_path}")
        image = face_recognition.load_image_file(image_path)
        encoding = face_recognition.face_encodings(image)

        if len(encoding) == 0:
            logger.warning("No face found in the image")
            return None, "No face found in the image."

        encoding = encoding[0]
        logger.info("Face encoding generated successfully")

        # Get all employee encodings from the database
        employee_encodings = frappe.get_all("Employee Face Encoding", fields=["name", "employee"])
        logger.info(f"Found {len(employee_encodings)} employee face encodings")

        best_match = None
        best_distance = float('inf')

        for employee in employee_encodings:
            face_encoding_details = frappe.get_all("Employee Face Encoding Detail",
                                                   filters={"parent": employee.name},
                                                   fields=["encoding"])
            for face_detail in face_encoding_details:
                known_encoding = np.array(eval(face_detail.encoding))
                face_distance = face_recognition.face_distance([known_encoding], encoding)[0]
                
                if face_distance < best_distance:
                    best_distance = face_distance
                    best_match = employee.employee

        if best_match and best_distance <= threshold:
            logger.info(f"Face recognized for employee {best_match} with distance {best_distance}")
            return best_match, f"Face recognized for employee {best_match}."
        else:
            logger.error(f"Face not recognized. Best match distance: {best_distance}")
            return None, "Face not recognized or not close enough to any registered employee."

    except Exception as e:
        logger.error(f"Error in checkin_user: {str(e)}")
        return None, "Error checking in user."

def save_spoof_image(image_path):
    """
    Saves the image where spoofing was detected to the 'spoofing_image' folder.
    """
    logger.info("Saving spoof image")
    current_datetime = now_datetime()
    filename = f"spoof_{current_datetime.strftime('%Y-%m-%d_%H:%M:%S')}.jpg"
    folder_path = frappe.get_site_path('public', 'files', 'spoofing_image')
    os.makedirs(folder_path, exist_ok=True)

    file_path = os.path.join(folder_path, filename)
    os.rename(image_path, file_path)
    logger.info(f"Spoof image saved to {file_path}")


@frappe.whitelist()
def verify_attendance(attendance_type, image, latitude, longitude, deviceNo):
    logger.info("verifying_attendance")
    try:
        # print("image: ",image)
         # Check if the image string contains a comma
        if ',' in image:
            # If it does, split and take the second part
            base64_data = image.split(',')[1]
        else:
            # If it doesn't, use the whole string
            base64_data = image
        image_path = base64_to_image(base64_data)
        logger.info(f"Image saved to {image_path}")

        matched_employee, message = checkin_user(image_path)
        logger.info(f"Checkin result: {message}")

        os.remove(image_path)
        logger.info(f"Temporary image removed: {image_path}")

        if matched_employee:
            employee_name = frappe.get_value("Employee", matched_employee, "employee_name")
            logger.info(f"Matched employee: {employee_name}")

            employee = frappe.get_doc("Employee", matched_employee)
            # Get employee's assigned branch
            emp_branch = frappe.get_doc("Branch", employee.branch)
            #get kiosk device details
            kiosk_device = frappe.get_list("Kiosk Devices", filters = {"activation_key": deviceNo}, fields=["name","branch","activation_key"])
            logger.info(f"kiosk_device: {kiosk_device}")
            if len(kiosk_device) == 0:
                return {"success": False, "error": f" Kiosk Mode is not Set for this Device"}
            # get branch assigned to device
            device_branch = frappe.get_doc("Branch", kiosk_device[0].branch)
            logger.info(f"device_branch: {device_branch}")

            if not is_device_within_geofence(float(latitude), float(longitude), device_branch.custom_location, deviceNo):
                logger.warning(f"Device {deviceNo} is outside the geofence")
                return {"success": False, "error": f" Device {kiosk_device[0].name} is not within the Office Location"}

            # Check if employee is within the geofence
            if not is_employee_within_geofence(float(latitude), float(longitude), emp_branch.custom_location, employee, employee_name):
                logger.warning(f"Employee {matched_employee} is outside the geofence")
                # frappe.throw("You are not within the Office Location")
                return {"success": False, "error": f"{employee_name} is not within the Office Location"}

            # code is commmented, and below code is added for by passing check_shift_and_create_attendance() and creating
            # attendance record because there is no need to check for late entry based on employee check-in, late entry or early exit
            # is added on attendance by auto attendance

            # is_late, attendance_status = check_shift_and_create_attendance(
            #     matched_employee, employee_name, attendance_type, latitude, longitude,
            # )

            attendance_status = create_attendance_record(
                matched_employee, employee_name, attendance_type, latitude, longitude,
            )
            
            if attendance_status in (True,False):
                if attendance_status:
                    # late_message = " (Late)" if is_late else ""
                    # logger.info(f"Attendance recorded for {employee_name}. Status: {attendance_status}, Late: {is_late}")
                    # code is commmented, and below code is added for by passing check_shift_and_create_attendance() and creating
                    # attendance record because there is no need to check for late entry based on employee check-in, late entry or early exit
                    # is added on attendance by auto attendance
                    logger.info(f"Attendance recorded for {employee_name}. Status: {attendance_status}")
                    
                    # Save the clock-in/clock-out image 
                    is_checkin = attendance_type == 'clockIn'
                    file_url = save_employee_image(matched_employee, base64_data, is_checkin)
                    logger.info(f"Employee image saved: {file_url}")
                    
                    return_msg = ""
                    if attendance_type == 'clockOut':
                        return_msg = f"{employee_name} Clock-Out Successfully"
                    elif attendance_type == 'clockIn':
                        # return_msg = f"{employee_name} Clock-In Successfully, {'but Late' if is_late else ''}"
                        return_msg = f"{employee_name} Clock-In Successfully"
                    
                    return {
                        "success": True, 
                        # "message": f"{employee_name} {'Clock Out' if attendance_type == 'clockOut' else 'Clock In'} Successfully, but {late_message}",
                        "message": return_msg,
                        "employee_name": employee_name,
                        # commented because we are not checking for late entry manually, late entry or early exit
                        # is added in attendance by auto attendance
                        # "is_late": is_late,
                        "status": attendance_status
                    }
                else:
                    return {"success": False, "error": "Face Recognition Failed, Please Try Again"}
            else:
                return {"success": False, "error": attendance_status}

            
        else:
            logger.warning(f"Attendance verification failed: {message}")
            return {"success": False, "error": "Face not recognized"}
            # return frappe.throw("Face not recognized")  

    except Exception as e:
        logger.error(f"Error in verify_attendance: {str(e)}")
        # return frappe.throw("An error occurred during verification. Please try again")  
        return {"success": False, "error": "An error occurred during verification. Please try again."}



def is_employee_within_geofence(employee_lat, employee_lon, branch_location, employee, employee_name):
    try:
        frappe.logger("geofence").info(f"check geolocation for Employee: {employee} Name: {employee_name}")

        branch_geojson = json.loads(branch_location)
        
        # Extract the center point and radius of the circle
        circle_feature = branch_geojson['features'][0]
        center_lon, center_lat = circle_feature['geometry']['coordinates']
        radius = circle_feature['properties']['radius']
        frappe.logger("geofence").info(f"allowed radius: {radius}")
        # Calculate the distance between the employee's location and the center of the circle
        employee_point = (employee_lat, employee_lon)
        center_point = (center_lat, center_lon)
        
        dist = distance.distance(employee_point, center_point).meters

        
        frappe.logger("geofence").info(f"Employee location: {employee_point}")
        frappe.logger("geofence").info(f"Branch center: {center_point}")
        frappe.logger("geofence").info(f"Distance: {dist} meters")
        frappe.logger("geofence").info(f"Allowed radius: {radius} meters")
        
        # Check if the distance is less than or equal to the radius
        is_within = dist <= radius
        frappe.logger("geofence").info(f"Is within geofence: {is_within}")
        
        return is_within
    except Exception as e:
        frappe.logger("geofence").error(f"Error in geofencing check: {str(e)}")
        return False


def is_device_within_geofence(device_lat, device_lon, branch_location, deviceNo):
    try:
        frappe.logger("geofence").info(f"check geolocation for device: {deviceNo} ")

        branch_geojson = json.loads(branch_location)
        
        # Extract the center point and radius of the circle
        circle_feature = branch_geojson['features'][0]
        center_lon, center_lat = circle_feature['geometry']['coordinates']
        radius = circle_feature['properties']['radius']
        frappe.logger("geofence").info(f"allowed radius: {radius}")
        # Calculate the distance between the device's location and the center of the circle
        device_point = (device_lat, device_lon)
        center_point = (center_lat, center_lon)
        
        dist = distance.distance(device_point, center_point).meters

        
        frappe.logger("geofence").info(f"Device location: {device_point}")
        frappe.logger("geofence").info(f"Branch center: {center_point}")
        frappe.logger("geofence").info(f"Distance: {dist} meters")
        frappe.logger("geofence").info(f"Allowed radius: {radius} meters")
        
        # Check if the distance is less than or equal to the radius
        is_within = dist <= radius
        frappe.logger("geofence").info(f"Is within geofence: {is_within}")
        
        return is_within
    except Exception as e:
        frappe.logger("geofence").error(f"Error in geofencing check: {str(e)}")
        return False


def create_attendance_record(employee_id, employee_name, attendance_type, latitude, longitude, is_late=False):
    logger.info(f"Creating attendance record for employee: {employee_id} name: {employee_name}")
    try:
        current_datetime = frappe.utils.now_datetime()
        current_date = frappe.utils.today()
        logger.info(f"getting attendance records of today {current_date} for the employee: {employee_id} name: {employee_name}")
        logger.info(f"type current_date: {type(current_date)} for type employee: {type(employee_id)} name: {employee_name}")

        # today_records = frappe.get_list("Attendance Record", 
        #                                 filters={
        #                                     "employee": employee_id,
        #                                     "attendance_date": '2024-08-15'
        #                                 },
        #                                 fields=["name", "check_in", "check_out"],
        #                                 order_by="check_in asc")

        # today_records = get_today_records(employee_id, current_date)

        # query = """
        #     SELECT name, check_in, check_out
        #     FROM `tabAttendance Record`
        #     WHERE employee = %s AND attendance_date = %s
        #     ORDER BY check_in ASC
        # """

        query = """
            SELECT name, employee, log_type, time
            FROM `tabEmployee Checkin`
            WHERE employee = %s AND DATE(time) = %s
            ORDER BY time ASC
        """

        today_records = frappe.db.sql(query, (employee_id, current_date), as_dict=True)
        
        logger.info(f"Found {len(today_records)} existing records for today")

        logger.info(f"today_records: {today_records}")
        if len(today_records) > 0:
            logger.info(f"last record: {today_records[-1]}")

        # Create GeoJSON FeatureCollection for the location
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Point",
                        "coordinates": [float(longitude), float(latitude)]
                    }
                }
            ]
        }
        location_json = json.dumps(geojson)


        logger.info(f"employee_id: {employee_id}")
        logger.info(f"type employee_id: {type(employee_id)}")
        employee = frappe.get_doc("Employee",employee_id)
        logger.info(f"employee: {employee}")

        # shift_assigned = frappe.get_list("Shift Assignment",
        #                                 filters={
        #                                     "employee": employee_id,
        #                                 },
        #                                 fields=["name", "shift_type"],
        #                                 order_by="start_date desc",
        #                                 limit=1
        #                             )

        query = """SELECT name, shift_type, docstatus
                   FROM `tabShift Assignment`
                   WHERE employee = %s AND docstatus = %s
                """
        shift_assigned = frappe.db.sql(query, (employee_id, 1), as_dict=True)


        logger.info(f"Shift Assigned: {shift_assigned}")
        if len(shift_assigned) == 1:
            logger.info(f"Shift Assigned: {shift_assigned[0]['shift_type']}")
        else:
            logger.info("No shift assignment found for the given employee.")
            return "Shift not Assigned for Employee"

        if attendance_type == "clockIn":
            if len(today_records) > 0:
                last_record = today_records[-1]
                
                if last_record.log_type != "OUT":
                    logger.warning("Incomplete clock-out found")
                    # frappe.throw("You have an incomplete clock-out. Please clock-out before clocking in again.")
                    return "You have an Incomplete Clock-Out. Please Clock-Out first"

                if current_datetime <= last_record.time:
                    logger.warning("Invalid clock-in time")
                    # frappe.throw("New clock-in time must be after the last clock-out time.")
                    return "New Clock-In time must be after the last Clock-Out time"

            employee_check_in = frappe.new_doc("Employee Checkin")
            employee_check_in.employee = employee_id
            employee_check_in.log_type = "IN"
            employee_check_in.device_id = location_json
            shift_doc = frappe.get_doc("Shift Type",shift_assigned[0]['shift_type'])
            logger.info(f"shift_doc: {shift_doc}")
            employee_check_in.shift = shift_doc
            # employee_check_in.is_late = is_late
            logger.info("New clock-in record created with location")
        
        elif attendance_type == "clockOut":
            if not today_records:
                logger.warning("No clock-in record found for today")
                # frappe.throw("No clock-in record found for today. Please clock-in before clocking out again.")
                return "No clock-in record found for today. Please clock-in before clocking out again"

            last_record = today_records[-1]
            
            if last_record.log_type == "OUT":
                logger.warning("Last record already has a clock-out")
                # frappe.throw("Your last attendance record is already clocked out. Please clock-in first.")
                return "Your last attendance record is already clocked out. Please clock-in first"

            # if current_datetime <= last_record.check_in:
            logger.info(f"current_datetime: {current_datetime} last_record.time: {last_record.time}")
            logger.info(f"type current_datetime: {type(current_datetime)} type last_record.time: {type(last_record.time)}")
            if current_datetime <= last_record.time:
                logger.warning("Invalid clock-out time")
                # frappe.throw("Clock-out time must be after the clock-in time.")
                return "Clock-out time must be after the clock-in time"

            employee_check_in = frappe.new_doc("Employee Checkin")
            employee_check_in.employee = employee_id
            employee_check_in.log_type = "OUT"
            employee_check_in.device_id = location_json
            shift_doc = frappe.get_doc("Shift Type",shift_assigned[0]['shift_type'])
            logger.info(f"shift_doc: {shift_doc}")
            employee_check_in.shift  = shift_doc
        
        else:
            logger.error(f"Invalid attendance type: {attendance_type}, Must be 'clockIn' or 'clockOut'")
            return False

        
        employee_check_in.insert(ignore_permissions=True)
        frappe.db.commit()
        logger.info(f"New employee_check_{'in' if attendance_type == 'clockIn' else 'out'} record created")
        return True
        
    except frappe.ValidationError as e:
        logger.error(f"Validation Error in create_attendance_record: {str(e)}")
        # raise
        return False
    except Exception as e:
        logger.error(f"Error in create_attendance_record: {str(e)}")
        logger.error(e)
        # raise frappe.ValidationError(f"Error creating attendance record: {str(e)}")
        return False



def get_today_records(employee_id, current_date):
    today_records = frappe.get_list("Attendance Record", 
                                        filters={
                                            "employee": employee_id,
                                            "attendance_date": current_date
                                        },
                                        fields=["name", "check_in", "check_out"],
                                        order_by="check_in asc")
    logger.info(f"Found {len(today_records)} existing records for today")
    print(f"Found {len(today_records)} existing records for today")
    return today_records


def get_employee_shifts():
    shift_assigned = frappe.get_list("Shift Assignment",
                                        filters={
                                            "employee": "HR-EMP-00992",
                                        },
                                        fields=["name", "shift_type"],
                                        order_by="start_date desc",
                                        limit=1
                                    )
    print("shift_assigned: ",shift_assigned)
    return shift_assigned