 <!-- custom code added - start -->
 <template>
    <div class="kiosk-mode fullscreen">
      <div
        v-if="toastMessage"
        :is-open="true"
        :duration=5000
        @didDismiss="toastMessage = ''"
        class="custom-toast"
        :class="{ 'success-toast': isSuccessMessage, 'error-toast': !isSuccessMessage }"
      >{{toastMessage}}</div>
      <div v-if="!isCameraActive">
        <div class="header">
          <img :src="image" alt="Company Logo" class="company-logo" />
        </div>
        <div  class="clock-buttons">
          <ion-button @click="startAttendanceProcess('clockIn')" color="primary" size="large">Clock In</ion-button>
          <ion-button @click="startAttendanceProcess('clockOut')" color="danger" size="large">Clock Out</ion-button>
        </div>
      </div>
      <div v-else class="camera-view">
        <div class="video-container">
          <video ref="videoRef" :src-object.prop.camel="stream" autoplay playsinline v-bind:style="{width: '100%', maxWidth: '500px'}"></video>
          <canvas ref="canvasRef" style="display: none;"></canvas>
        </div>
        <div class="button-container">
          <!-- <ion-button @click="captureAndSubmit" expand="block" color="{currentAction === 'clockIn' ? 'primary' : 'danger'}">
            {{ `${currentAction === 'clockIn' ? 'Clock In' : 'Clock Out'}` }}
          </ion-button> -->
          <!-- {{ `${currentAction === 'clockIn'}` ? 
              <ion-button @click="captureAndSubmit" expand="block" color="primary">
                'Clock In'
              </ion-button>
              : 
              <ion-button @click="captureAndSubmit" expand="block" color="danger">
                'Clock Out'
              </ion-button>
          }} -->
          <div v-if="currentAction === 'clockIn'">
            <ion-button @click="captureAndSubmit" expand="block" color="primary">
              Clock In
            </ion-button>
          </div>
          <div v-else>
            <ion-button @click="captureAndSubmit" expand="block" color="danger">
              Clock Out
            </ion-button>
          </div>
        </div>
      </div>
      
    </div>
  </template>
  
  
  <script setup>
    import { ref, onMounted, onUnmounted, watch } from 'vue';
    import { IonButton, IonToast } from '@ionic/vue';
    import { createResource } from 'frappe-ui';
    import { computed } from 'vue';
    import image from "../../public/Wellness Logo.png"
  
  
    const videoRef = ref(null);
    const canvasRef = ref(null);
    const stream = ref(null);
    const isCameraActive = ref(false);
    const currentAction = ref(null);
    const geolocation = ref(null);
    const toastMessage = ref('');
  
    console.log("in kioskAttendance")
  
    const startAttendanceProcess = (action) => {
      toastMessage.value = ''
      currentAction.value = action;
      getGeolocation();
      activateCamera();
    };
  
    const getGeolocation = (successCallback, errorCallback) => {
    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        getCoor,
        errorCoor,
        {
          // maximumAge: 60000,  // Cache the position for 1 minute (60000 ms)
          timeout: 5000,      // Wait for 5 seconds before timing out
          enableHighAccuracy: true
        }
      );
    } else {
      toastMessage.value = "Geolocation is not supported by this browser";
      if (errorCallback) errorCallback(new Error("Geolocation not supported"));
    }
  
    function getCoor(position) {
      const newGeolocation = {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracy: position.coords.accuracy,
        timestamp: position.timestamp
      };
      geolocation.value = newGeolocation;
      console.log("Geolocation fetched:", geolocation.value);
      if (successCallback) successCallback(newGeolocation);
    }
  
    function errorCoor(error) {
      console.error("Error getting geolocation:", error);
      let errorMessage = "Unable to get location. ";
      switch(error.code) {
        case error.PERMISSION_DENIED:
          errorMessage += "Please enable location services.";
          break;
        case error.POSITION_UNAVAILABLE:
          errorMessage += "Location information is unavailable.";
          break;
        case error.TIMEOUT:
          errorMessage += "The request to get location timed out.";
          break;
        default:
          errorMessage += "An unknown error occurred.";
      }
      toastMessage.value = errorMessage;
      if (errorCallback) errorCallback(error);
    }
  };
  
  
    const activateCamera = async () => {
      try {
        console.log("fetching location")
        const userAgent = navigator.userAgent.toLowerCase();
        console.log("userAgent: ",userAgent)
        const isTablet = /(ipad|tablet|(android(?!.*mobile))|(windows(?!.*phone)(.*touch))|kindle|playbook|silk|(puffin(?!.*(IP|AP|WP))))/.test(userAgent);
        console.log("isTablet: ",isTablet)
        const isMobile = /Android|webOS|iPhone|iPod|BlackBerry|IEMobile|Opera Mini/i.test(userAgent);
        console.log("isMobile: ", isMobile);
        // //if device is tablet then using back camera for face recognition otherwise using front camera
        if(isTablet || isMobile){
         stream.value = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
        }else{
         stream.value = await navigator.mediaDevices.getUserMedia({ video: true });
        }
        // stream.value = await navigator.mediaDevices.getUserMedia({ video: true });
        
        isCameraActive.value = true;
        console.log("Camera activated successfully");
      } catch (err) {
        console.error("Error accessing the camera", err);
        toastMessage.value = "Error accessing the camera. Please make sure it's connected and permissions are granted.";
      }
    };
  
  
    const captureImage = () => {
      const video = videoRef.value;
      const canvas = canvasRef.value;
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      canvas.getContext('2d').drawImage(video, 0, 0);
      return canvas.toDataURL('image/jpeg').split(',')[1];
    };
  
    const captureAndSubmit = async () => {
      const base64Image = captureImage();
      closeCamera();
      submitAttendance(base64Image);
    };
  
    const closeCamera = () => {
      if (videoRef.current && videoRef.current.srcObject) {
              const tracks = videoRef.current.srcObject.getTracks();
              tracks.forEach(track => track.stop());
              videoRef.current.srcObject = null;
            }
      if (stream.value) {
        stream.value.getTracks().forEach(track => track.stop());
      }
      isCameraActive.value = false;
    };
  
    const submitAttendance = async (base64Image) => {
      toastMessage.value = "Processing";
      console.log("submitting attendance")
      try {
        console.log("in try of submitAttendance")
  
        const addAttendance = await createResource({
          url: 'hrms.hr.doctype.api.verify_attendance',
          method: 'POST',
          params: {
            attendance_type: currentAction.value,
            image: base64Image,
            latitude: geolocation.value.latitude,
            longitude: geolocation.value.longitude,
            deviceNo: localStorage.getItem("kioskDeviceNo")
          },
          auto: false,
          onError(error) {
            console.log("attendance failed, error: ",error);
            console.log("toastMessage: ",toastMessage);
            toastMessage.value = "Face not recognized. Please try again.";
          },
          // on successful response
          onSuccess(data) {
            console.log("attendance success, data: ",data);
            if(data.success){
              console.log("data.success in if")
              toastMessage.value = data.message;
            }else{
              console.log("data.success in else")
              toastMessage.value = data.error;
            }
            
          },
        });
        await addAttendance.fetch();
        // const response = await addAttendance.fetch();
        // console.log("response: ",response)
        // console.log("response.message: ",response.message)
        // if (response.message && response.message.success) {
        //   console.log("attendance success");
        //   toastMessage.value = `Successfully ${currentAction.value === 'clockIn' ? 'clocked in' : 'clocked out'}`;
        // } else {
        //   console.log("attendance failed");
        //   toastMessage.value = response.message.error || "Face not recognized. Please try again.";
        // }
      } catch (error) {
        console.error("Error verifying attendance", error);
        toastMessage.value = "Error verifying attendance. Please try again.";
      }
      
      currentAction.value = null;
      geolocation.value = null;
    };
  
    onMounted(() => {
      console.log("in onMounted()")
      // Request fullscreen mode on component mount
      document.documentElement.requestFullscreen().catch((err) => {
        console.error('Error entering fullscreen:', err);
      });
      // document.documentElement.requestFullscreen()
  });

    onUnmounted(() => {
      if (document.fullscreenElement) {
        document.exitFullscreen();
      }
      closeCamera();
    });
  
    const isSuccessMessage = computed(() => {
      console.log("in isSuccessMessage")
      return toastMessage.value.includes('Successfully');
    });
  
    watch(toastMessage, (newValue) => {
    if (newValue) {
      if ((toastMessage.value != "Face not recognized. Please try again" || toastMessage.value != "Error accessing the camera. Please make sure it's connected and permissions are granted")){
        console.log("toast message settimeout")
        setTimeout(() => {
          toastMessage.value = '';
        }, 4000);
      }
    }
  });
  
  
  </script>
  
  <style scoped>
  .kiosk-mode {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    height: 100vh;
    background-color: #f4f4f4;
  }
  .clock-buttons{
    display: flex;
    /* flex-direction: column; */
    gap: 20px;
    margin-top: 20px;
  }
  .camera-view {
    display: flex;
    flex-direction: column;
    gap: 20px;
    margin-top: 20px;
  }
  
  .fullscreen {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    right: 0;
    overflow: auto;
    z-index: 9999;
  }
  
  video {
    width: 100%;
    max-width: 500px;
    margin-bottom: 20px;
  }
  
  .custom-toast {
    position: fixed;
    top: 16px;
    right: 0;
    margin: 20px;
    width: fit-content;
    border-radius: 5px;
    background: var(--toast-background-color);
    color: white;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    padding: 10px 20px;
  }
  
  .custom-toast::part(container) {
    position: fixed;
    top: 16px;
    right: 16px;
    left: unset;
    bottom: unset;
    width: auto;
    max-width: calc(100% - 32px);
    transition: opacity 0.3s ease-in-out;
  }
  
  .success-toast {
    --toast-background-color: #4CAF50;
  }
  
  .error-toast {
    --toast-background-color: #f44336;
  }
  </style>
  <!-- custom code added - end -->
