// Copyright (c) 2025, Salman and contributors
// For license information, please see license.txt

frappe.query_reports["Complain Analytics"] = {
    "filters": [
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        },
        {
            "fieldname": "technician",
            "label": __("Technician"),
            "fieldtype": "Link",
            "options": "Technician"
        },
        {
            "fieldname": "complainer_phone",
            "label": __("Complainer Phone"),
            "fieldtype": "Data"
        },
        {
            "fieldname": "territory",
            "label": __("Territory"),
            "fieldtype": "Link",
            "options": "Territory"
        },
        {
            "fieldname": "workflow_state",
            "label": __("Status"),
            "fieldtype": "Link",
            "options": "Workflow State"
        }
    ],
    formatter: function (value, row, column, data, default_formatter) {
        if (column.fieldname === "time_to_resolution" && value != null) {
            const time = parseFloat(value) || 0;
            const display = time.toFixed(2);

            let bg = "#80ff80ff";
            if (time > 24 && time <= 48) bg = "#FFD700";
            else if (time > 48 && time <= 72) bg = "#FF6347";
            else if (time > 72) bg = "#FF0000";

            return `
          <div style="
              background:${bg};
              display:block;
              margin:-8px;
              padding:8px;
              box-sizing:border-box;
              text-align:right;
              font-weight:700;
          ">
            ${display}
          </div>
        `;
        }

        return default_formatter(value, row, column, data);
    }

};
