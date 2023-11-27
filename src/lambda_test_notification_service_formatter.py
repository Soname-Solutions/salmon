import json
from lib.notification_service.formatter_provider import formatters


def lambda_handler(event, context):
    event_info = json.loads(event)
    delivery_options_info = event_info.get("delivery_options")
    data_info = event_info.get("data")

    delivery_method = delivery_options_info.get("delivery_method")

    if delivery_method is None:
        raise KeyError("Delivery method is not set.")

    table_info = data_info.get("table")
    table_header = table_info.get("table_header")
    table_items = table_info.get("table_items")

    formatter = formatters.get(delivery_method)
    table = formatter.get_table(table_items, table_header)

    print(table)


if __name__ == "__main__":
    test_event = """
    {
   "delivery_options":{
      "sender_email":"salmon-no-reply@soname.de",
      "recipients":[
         "vasya_pupking@soname.cn"
      ],
      "delivery_method":"AWS_SES"
   },
   "data":{
      "subject":"[monitored env 1] Glue Job 1 has failed",
      "header":"Oh my gosh. Something went wrong",
      "table":{
         "table_items":[
            {
               "cells":[
                  "AWS Account",
                  "1234"
               ]
            },
            {
               "cells":[
                  "Time",
                  "2022-09-09 09:00:00"
               ]
            }
         ]
      }
   }
}
    """
    context = ""

    lambda_handler(test_event, context)
