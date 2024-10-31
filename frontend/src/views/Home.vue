<template>
	<BaseLayout>
		<template #body>
			<div class="flex flex-col items-center my-7 p-4 gap-7">
				<CheckInPanel />
				<QuickLinks :items="quickLinks" title="Quick Links" />
				<RequestPanel />
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { markRaw } from "vue"

import CheckInPanel from "@/components/CheckInPanel.vue"
import QuickLinks from "@/components/QuickLinks.vue"
import BaseLayout from "@/components/BaseLayout.vue"
import RequestPanel from "@/components/RequestPanel.vue"
import LeaveIcon from "@/components/icons/LeaveIcon.vue"
import ExpenseIcon from "@/components/icons/ExpenseIcon.vue"
import EmployeeAdvanceIcon from "@/components/icons/EmployeeAdvanceIcon.vue"
import SalaryIcon from "@/components/icons/SalaryIcon.vue"
import KioskIcon from "@/components/icons/KioskIcon.vue"
// custom code added - start
import { userResource } from "@/data/user";


const userRoles = userResource?.data?.roles || [];
console.log("User roles:", userRoles);
// custom code added - end

const quickLinks = [
	{
		icon: markRaw(LeaveIcon),
		title: "Request Leave",
		route: "LeaveApplicationFormView",
	},
	{
		icon: markRaw(ExpenseIcon),
		title: "Claim an Expense",
		route: "ExpenseClaimFormView",
	},
	{
		icon: markRaw(EmployeeAdvanceIcon),
		title: "Request an Advance",
		route: "EmployeeAdvanceFormView",
	},
	{
		icon: markRaw(SalaryIcon),
		title: "View Salary Slips",
		route: "SalarySlipsDashboard",
	},
	// custom code added - start
	{
		icon: markRaw(KioskIcon),
		title: "Kiosk Attendance",
		route: "KioskAttendance",
		allowedRoles: ["HR Manager"],
	},
	{
		icon: markRaw(KioskIcon),
		title: "Kiosk Mode",
		route: "KioskMode",
		allowedRoles: ["HR Manager"],
	},
	// custom code added - end
]

	// custom code added - start
	const filteredQuickLinks = filterQuickLinksByRole(quickLinks, userRoles);

	function filterQuickLinksByRole(quickLinks, userRoles) {
	return quickLinks.filter((link) => {
		if(link.allowedRoles){
			console.log(`link ${link} Allowed Roles ${link.allowedRoles}`);
			const allowedRoles = link.allowedRoles || []; // Default to empty array
			console.log('retutn: ',userRoles.some((userRole) => allowedRoles.includes(userRole)))
			return userRoles.some((userRole) => allowedRoles.includes(userRole));
		}
		return true;
	
	});
	}
	// custom code added - end

</script>
