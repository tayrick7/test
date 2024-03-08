# Database_v1
First, make sure the following libraries and MySQL server are installed in your computer.
```
import os
import mysql.connector as msql
from mysql.connector import Error
import pandas as pd
from flask import Flask, request
from flask_restx import Api, Resource
from werkzeug.datastructures import FileStorage
```
Once you have the Mysql server installed, you should have  server name and password ready. Change following to your own name and password:
```
db_user = 'root'
db_password = 'mysql123' # change to your mysql password
```

To run the script, either type `python database_v1.py` in the terminal or open pycharm/vscode and click run. Then it should pop a message saying the server is running on address-xxx. Copy and paste the address to the browser and will see a interface that you can test the function of database.

To test different users, I simply use different port numbers to represent different users. Change port number in `app.run(debug=True,port=5000)`.
Each user will have their database based on their `user_id`. Here, the `user_id` is port number.
