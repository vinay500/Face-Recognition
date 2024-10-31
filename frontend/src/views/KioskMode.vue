 <!-- custom code added - start -->
 <template>
    <ion-page>
      <ion-content :fullscreen="true">
        <ion-grid>
          <ion-row>
            <ion-col size="12">
              <FormView
                v-if="formFields.data"
                doctype="Kiosk Devices"
                v-model="formData"
                :isSubmittable="true"
                :fields="getFilteredFields(formFields.data)"
                :id="props.id"
                :showFormButton="false"
              />
              <!-- @validateForm="validateForm" -->
            </ion-col>
          </ion-row>
          <ion-row>
            <ion-col size="auto" style="display: flex; justify-content: center; width: 50%; padding: 0.5rem;">
              <Button
                @click="validateForm()"
                class="w-24 py-5"
                variant="solid"
                style="width: 80%;"
              >
                Save
              </Button>
            </ion-col>
          </ion-row>
        </ion-grid>
      </ion-content>
    </ion-page>
  </template>
  
  <script setup>
  import { IonPage, IonContent } from "@ionic/vue"
  import { createResource } from "frappe-ui"
  import { ref, watch, inject } from "vue"
  
  import FormView from "@/components/FormView.vue"
  import { mapMutations } from 'vuex';
  import router from "../router"
  // import store from '../store/kioskMode.js';
  
  const { setKioskMode } = mapMutations(['setKioskMode']);
  const dayjs = inject("$dayjs")
  const store = inject('store');
  
  
  const props = defineProps({
    id: {
      type: String,
      required: false,
    },
  })
  
  // reactive object to store form data
  const formData = ref({})
  
  // get form fields
  const formFields = createResource({
    url: "hrms.api.get_doctype_fields",
    params: { doctype: "Kiosk Devices" },
    onSuccess(data) {
      // No transformation needed for Kiosk Devices, keep all fields
    },
  })
  formFields.reload()
  
  // helper functions
  function getFilteredFields(fields) {
    // Filter to include only the "activation_key" field
    return fields.filter((field) => field.fieldname === "activation_key")
  }
  
  const findKioskDeviceByActivationKey = async () =>  {
    console.log("formData.value.activation_key: ",formData.value.activation_key)
    const findKioskDevice = await createResource({
      url: 'hrms.hr.doctype.update_last_sync_checkin.findKioskDevices',
      method: 'POST',
      params: {
        activation_key: formData.value.activation_key
      },
      auto: false,
      onError(error) {
        console.error('Error in findKioskDevicesByActivationKey():', error);
      },
      onSuccess(data) {
        console.log("success, data:",data);
        console.log("store: ",store);
        console.log("store.state:",store.state);
        console.log("Before updating kioskMode: ", store.state.kioskMode);
        if (data.success) {
          console.log("Before updating kioskMode: ", store.state.kioskMode);
          // setKioskMode(true);
          router.push('/kiosk').then(() => {
              console.log("router.push successfully");
              // store.dispatch('updateKioskMode', true);
              // console.log("After updating kioskMode: ", store.state.kioskMode);
              localStorage.setItem('kioskMode', true);
              localStorage.setItem('kioskDeviceNo', data.kioskDeviceKey);
            }).catch(error => {
              console.error("Error router pushing: ", error);
            });
        } else {
          console.error('Error, data: ',data);
          const activationKeyField = formFields.data.find(
        (field) => field.fieldname === "activation_key");
          activationKeyField.error_message = data.message;
        }
      },
    })
    await findKioskDevice.fetch();
    console.log("findKioskDevice.params: ",findKioskDevice.params);
  }
  
  
  async function validateForm() {
    console.log("in validateForm()")
    if (!formData.value.activation_key) {
      console.log("activation key is empty")
      const activationKeyField = formFields.data.find(
        (field) => field.fieldname === "activation_key"
      );
      activationKeyField.error_message = "Activation key cannot be empty";
      return false;
    }
    console.log("activation_key  isn't empty")
    console.log("activation_key: ",formData.value.activation_key)
    let res = await findKioskDeviceByActivationKey();
    console.log("res: ",res);
  }
  
  
  </script>
  
  <!--  custom code added - end -->