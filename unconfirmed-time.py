import requests
import os
import time
from datetime import datetime

# Save your access token for RM and Gchat webhook in your environments variables.
ACCESS_TOKEN = os.environ.get('TOKEN')
WEBHOOK = os.environ.get('WEBHOOK')
BASEURL = "https://api.rm.smartsheet.com"
REPORTS_API = "/api/v1/reports/rows"
USERS_API = "/api/v1/users?per_page=100&page=1&fields=email"


def nag(dry_run, timeframe):
    # Setting the report parameters
    report_parameters = {
        "view": "time_fees_hours",
        "time_frame": timeframe,
        "group_by": ["project_id", "user_id"],
        "filters": {
            "people_tags": {
                "operation": "exclusion",
                "values": ["Bench"]
            },
            "entry_type": {
                "operation": "inclusion",
                "values": ["Unconfirmed"]
            }
        },
        "today": "{}".format(datetime.today().strftime('%Y-%m-%d')),
        "calc_incurred_using": "confirmed-unconfirmed"
    }

    # Getting the report for all unconfirmed time
    report_result = requests.post("{}{}".format(BASEURL, REPORTS_API),
                                  headers={'Content-Type': 'application/json', 'auth': '{}'.format(ACCESS_TOKEN)},
                                  json=report_parameters)

    unconfirmed_report = report_result.json()

    if not unconfirmed_report["rows"]:
        return "No unconfirmed timesheet for the given timeframe."

    naughty_ids = []
    for row in unconfirmed_report["rows"]:
        naughty_ids.append(row['user_id'])
        if dry_run:
            print("User: {} has unconfirmed time for last week.".format(row["user_name"]))

    # Getting the email for all naughty list users
    email_result = requests.get("{}{}".format(BASEURL, USERS_API),
                                headers={'Content-Type': 'application/json', 'auth': '{}'.format(ACCESS_TOKEN)})

    user_list_result = email_result.json()

    for user in user_list_result["data"]:
        if user["id"] in naughty_ids:
            # Sleeping here because the API has pretty restrictive limitations
            time.sleep(1)
            custom_fields_url = "/api/v1/users/{}?fields=custom_field_values".format(user["id"])

            # Getting the custom fields for this naughty list user
            custom_result = requests.get("{}{}".format(BASEURL, custom_fields_url),
                                         headers={'Content-Type': 'application/json',
                                                  'auth': '{}'.format(ACCESS_TOKEN)})

            user_custom_fields = custom_result.json()
            external_id = user_custom_fields["custom_field_values"]["data"][2]["value"]

            google_chat_message = {
                "text": "<users/{}> You have unconfirmed time for last week.  "
                        "Please login to Resource Manager and complete your timesheet.".format(external_id)
            }

            # Google Chat Message the User to let them know to update their timesheet
            requests.post(WEBHOOK,
                          headers={"Content-Type": "application/json; charset=UTF-8"},
                          json=google_chat_message)


if __name__ == '__main__':
    print(nag(dry_run=True, timeframe="last_week"))
