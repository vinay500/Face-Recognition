import frappe
from frappe.utils import now_datetime, add_to_date
from hrms.hr.doctype.shift_type.shift_type import process_auto_attendance_for_all_shifts


frappe.utils.logger.set_log_level("INFO")
logger = frappe.logger("debug", allow_site=True, file_count=10)

def hourly_attendance_processing():
    logger.info("in hourly_attendance_processing with scheduled")
    try:
        # Get all active shift types with auto attendance enabled
        shift_types = frappe.get_all(
            "Shift Type",
            filters={"enable_auto_attendance": 1},
            fields=["name", "last_sync_of_checkin"]
        )
        logger.info(f"shift_types: {shift_types}")
        logger.info(f"current_time: {now_datetime()}")
        for shift in shift_types:
            # Update last_sync_of_checkin to current time
            logger.info(f"shift: {shift}")
            current_time = now_datetime()
            frappe.db.set_value("Shift Type", shift.name, "last_sync_of_checkin", current_time)
            # Process attendance for this shift
            shift_doc = frappe.get_doc("Shift Type", shift.name)
            shift_doc.save(ignore_permissions=True)
            shift_doc.process_auto_attendance()
        frappe.db.commit()
        logger.info("shift last sync updated")
        frappe.logger().info(f"Hourly attendance processing completed at {current_time}")
    except Exception as e:
        logger.info("shift last sync error: ",str(e))
        frappe.logger().error(f"Error in hourly attendance processing: {str(e)}")
        frappe.db.rollback()



@frappe.whitelist()
def findKioskDevices(activation_key):
    print("activation_key: ",activation_key)
    try:
        kiosk_devices = frappe.get_list("Kiosk Devices",
                                        fields = ["name"],
                                        filters = {
                                            "activation_key": activation_key,
                                            "docstatus":1
                                        }
                                    )
        print("kiosk_devices: ",kiosk_devices)
        if len(kiosk_devices) == 1:
            return {"success": True, "message": "Single Kiosk Device Found  with Activation Key", "kioskDeviceKey": activation_key }
        elif len(kiosk_devices) == 0:
            return {"success": False, "message": "No Kiosk Devices Found with Activation Key"}
        elif len(kiosk_devices) > 1:
            return {"success": False, "message": "More than One Kiosk Devices Found  with Activation Key"}
        
    except Exception as e:
        print("exception in findKioskDevices, e: ",e)
        return {"success": False, "message": "Error in Finding Kiosk Devices"}
        


@frappe.whitelist()
def find_device_kiosk():
    return "returning api_method()"

