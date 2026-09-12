from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask import send_file
from fpdf import FPDF
from dotenv import load_dotenv
import os
import pymysql
import re
import random as r
import datetime as dt
import csv
import io
load_dotenv()



app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")
@app.after_request
def add_no_cache(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Database connection
def get_db_connection():
    return pymysql.connect(
        host=os.environ.get("DB_HOST"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        database=os.environ.get("DB_NAME"),
        port=int(os.environ.get("DB_PORT", 3306)),
        cursorclass=pymysql.cursors.DictCursor
    )


@app.route("/")
def home():
    return render_template("home.html")

@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    # When opening the login page
    if request.method == "GET":
        return render_template("login.html")

    # Get form data
    role = request.form.get("role")
    username = request.form.get("username")
    password = request.form.get("password")

    # =========================
    # ADMIN LOGIN
    # =========================

    if role == "admin":
        admin_username = os.environ.get("ADMIN_USERNAME")
        admin_password = os.environ.get("ADMIN_PASSWORD")

        if username == admin_username and password == admin_password:
            session["role"] = "admin"
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid Admin Username or Password!", "danger")
            return redirect(url_for("login"))

    # =========================
    # EMPLOYEE LOGIN
    # =========================

    elif role == "employee":

        empid = request.form.get("empid")

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT e.login_id,
                e.login_pass,
                e.empid,
                emp.emp_status,
                emp.name
            FROM emplogdetails e
            JOIN employee emp ON e.empid = emp.empid
            WHERE BINARY e.login_id=%s
            AND BINARY e.login_pass=%s
            AND e.empid=%s
            """,
            (username, password, empid)
        )

        employee = cursor.fetchone()

        if employee:
            if employee["emp_status"] == "Former":

                flash(
                    "Your employee account is no longer active. Please contact the administrator!",
                    "danger"
                )

            else:
                session["role"] = "employee"
                session["empid"] = empid
                session["name"] = employee["name"]

                cursor.close()
                connection.close()

                return redirect(url_for("employee_dashboard"))

        else:
            flash(
                "Invalid Employee ID, Username or Password!",
                "danger"
            )

        cursor.close()
        connection.close()

        return redirect(url_for("login"))

    # CUSTOMER LOGIN
    # =========================

    elif role == "customer":
        custid = request.form.get("custid")

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT c.customerid,
                c.name,
                l.login_id,
                l.login_pass,
                a.account_type
            FROM customerlogdetails l
            JOIN customers c
                ON l.customerid = c.customerid
            JOIN accounts a
                ON c.customerid = a.customerid
            WHERE l.customerid=%s
            AND BINARY l.login_id=%s
            AND BINARY l.login_pass=%s
            """,
            (custid, username, password)
        )

        customer = cursor.fetchone()

        if customer:

            if customer["account_type"] == "Disabled":

                flash(
                    "Your account has been disabled. Please contact the bank!",
                    "danger"
                )

            else:

                session["role"] = "customer"
                session["custid"] = custid
                session["name"] = customer["name"]

                cursor.close()
                connection.close()

                return redirect(url_for("customer_dashboard"))

        else:

            flash(
                "Invalid Customer ID, Username or Password!",
                "danger"
            )

        cursor.close()
        connection.close()

        return redirect(url_for("login"))

@app.route("/employee/dashboard")
def employee_dashboard():

    if session.get("role") not in ["employee", "admin"]:
        return redirect(url_for("home"))

    return render_template("employee_dashboard.html")

@app.route("/admin/dashboard")
def admin_dashboard():

    if session.get("role") != "admin":
        return redirect(url_for("home"))

    connection = get_db_connection()
    cursor = connection.cursor()

    # Total Customers
    cursor.execute("SELECT COUNT(*) AS total FROM customers")
    total_customers = cursor.fetchone()["total"]

    # Total Employees
    cursor.execute("SELECT COUNT(*) AS total FROM employee")
    total_employees = cursor.fetchone()["total"]

    # Total Accounts
    cursor.execute("SELECT COUNT(*) AS total FROM accounts")
    total_accounts = cursor.fetchone()["total"]

    # Total Transactions
    cursor.execute("SELECT COUNT(*) AS total FROM transactions")
    total_transactions = cursor.fetchone()["total"]

    # Total Bank Balance
    cursor.execute("SELECT COALESCE(SUM(balance), 0) AS total FROM accounts")
    total_balance = cursor.fetchone()["total"]

    cursor.close()
    connection.close()

    return render_template(
        "admin_dashboard.html",
        total_customers=total_customers,
        total_employees=total_employees,
        total_accounts=total_accounts,
        total_transactions=total_transactions,
        total_balance=total_balance
    )

@app.route("/admin/register-employee", methods=["GET", "POST"])
def register_employee():

    if session.get("role") != "admin":
        return redirect(url_for("home"))

    if request.method == "POST":

        name = request.form.get("name").capitalize()
        dob = request.form.get("dob")
        phone = request.form.get("phone")
        email = request.form.get("email")
        salary = request.form.get("salary")
        branchid = request.form.get("branchid")
        username = request.form.get("username")
        password = request.form.get("password")

        # Email validation
        email_pattern = re.compile(
            r'^[\w\.-]+@([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$'
        )

        if not email_pattern.match(email):
            return "Invalid Email"

        # Phone validation
        if len(phone) != 10 or not phone.isdigit():
            return "Phone number must contain 10 digits"

        # Password validation
        password_pattern = re.compile(
            r'^(?=.*[A-Z])(?=.*[0-9])(?=.*[@$#%^&*()!]).{8,}$'
        )

        if not password_pattern.match(password):
            return """
            Password must contain:
            - At least 8 characters
            - One uppercase letter
            - One digit
            - One special character
            """

        connection = get_db_connection()
        cursor = connection.cursor()

        # Check if username already exists
        cursor.execute(
            "SELECT * FROM emplogdetails WHERE login_id=%s",
            (username,)
        )

        existing_user = cursor.fetchone()

        if existing_user:
            cursor.close()
            connection.close()

            return "Username already exists"

        # Insert employee
        cursor.execute(
            """
            INSERT INTO employee
            (name, dob, phone, email, salary, branchid)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (name, dob, phone, email, salary, branchid)
        )

        connection.commit()

        # Get newly created employee ID
        empid = cursor.lastrowid

        # Create employee login
        cursor.execute(
            """
            INSERT INTO emplogdetails
            VALUES (%s, %s, %s)
            """,
            (username, password, empid)
        )

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("admin_dashboard"))

    return render_template("register_employee.html")

@app.route("/admin/search-customer", methods=["GET", "POST"])
def search_customer():
    if session.get("role") != "admin":
        return redirect(url_for("home"))

    customers = []

    if request.method == "POST":
        search = request.form.get("search", "").strip()

        connection = get_db_connection()
        cursor = connection.cursor()

        query = """
            SELECT customerid, name, dob, phone, email
            FROM customers
            WHERE CAST(customerid AS CHAR) LIKE %s
               OR name LIKE %s
               OR phone LIKE %s
               OR email LIKE %s
        """

        search_value = f"%{search}%"

        cursor.execute(
            query,
            (search_value, search_value, search_value, search_value)
        )

        customers = cursor.fetchall()

        cursor.close()
        connection.close()

    return render_template(
        "search_customer.html",
        customers=customers
    )

@app.route("/admin/search-transactions", methods=["GET", "POST"])
def search_transactions():
    if session.get("role") != "admin":
        return redirect(url_for("home"))

    transactions = []

    if request.method == "POST":

        search = request.form.get("search", "").strip()

        connection = get_db_connection()
        cursor = connection.cursor()

        query = """
            SELECT transaction_id,
                   accountid,
                   type,
                   amount,
                   date_time,
                   related_account,
                   balance_after,
                   trx_code
            FROM transactions
            WHERE CAST(accountid AS CHAR) LIKE %s
               OR type LIKE %s
               OR trx_code LIKE %s
               OR CAST(transaction_id AS CHAR) LIKE %s
            ORDER BY date_time DESC
        """

        search_value = f"%{search}%"

        cursor.execute(
            query,
            (
                search_value,
                search_value,
                search_value,
                search_value
            )
        )

        transactions = cursor.fetchall()

        cursor.close()
        connection.close()

    return render_template(
        "search_transactions.html",
        transactions=transactions
    )


@app.route("/admin/delete-employee", methods=["GET", "POST"])
def delete_employee():

    if session.get("role") != "admin":
        return redirect(url_for("home"))

    if request.method == "POST":

        empid = request.form.get("empid")

        connection = get_db_connection()
        cursor = connection.cursor()

        # Check if employee exists
        cursor.execute(
            "SELECT * FROM employee WHERE empid=%s",
            (empid,)
        )

        employee = cursor.fetchone()

        if employee:

            cursor.execute(
                """
                UPDATE employee
                SET emp_status='Former'
                WHERE empid=%s
                """,
                (empid,)
            )

            connection.commit()

            cursor.close()
            connection.close()

            flash(f"Employee ID {empid} has been marked as Former successfully!", "success")


            return redirect(url_for("delete_employee"))

        cursor.close()
        connection.close()

        flash("Invalid Employee ID!", "danger")
        return redirect(url_for("delete_employee"))

    return render_template("delete_employee.html")

@app.route("/admin/reactivate-employee", methods=["GET", "POST"])
def reactivate_employee():

    if session.get("role") != "admin":
        return redirect(url_for("home"))

    if request.method == "POST":

        empid = request.form.get("empid")

        connection = get_db_connection()
        cursor = connection.cursor()

        # Check employee
        cursor.execute(
            "SELECT empid, name, emp_status FROM employee WHERE empid=%s",
            (empid,)
        )

        employee = cursor.fetchone()

        if not employee:
            flash("Invalid Employee ID!", "danger")

        elif employee["emp_status"] == "Active":
            flash(f"Employee ID {empid} is already Active!", "warning")

        else:
            cursor.execute(
                """
                UPDATE employee
                SET emp_status='Active'
                WHERE empid=%s
                """,
                (empid,)
            )

            connection.commit()

            flash(
                f"Employee ID {empid} has been made Active successfully!",
                "success"
            )

        cursor.close()
        connection.close()

        return redirect(url_for("reactivate_employee"))

    return render_template("reactivate_employee.html")

@app.route("/admin/view-transactions")
def view_transactions():

    if session.get("role") != "admin":
        return redirect(url_for("home"))

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM transactions")
    transactions = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "view_transactions.html",
        transactions=transactions
    )
@app.route("/change-password", methods=["GET", "POST"])
def change_password():

    if session.get("role") not in ["employee", "customer"]:
        return redirect(url_for("home"))

    if request.method == "POST":

        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        # Check new passwords
        if new_password != confirm_password:
            flash("New passwords do not match!", "danger")
            return redirect(url_for("change_password"))
        # Password validation
        if len(new_password) < 8:
            flash("Password must be at least 8 characters long!", "danger")
            return redirect(url_for("change_password"))

        if not re.search(r"[A-Z]", new_password):
            flash("Password must contain at least one uppercase letter!", "danger")
            return redirect(url_for("change_password"))

        if not re.search(r"[a-z]", new_password):
            flash("Password must contain at least one lowercase letter!", "danger")
            return redirect(url_for("change_password"))

        if not re.search(r"[0-9]", new_password):
            flash("Password must contain at least one number!", "danger")
            return redirect(url_for("change_password"))

        if not re.search(r"[^A-Za-z0-9]", new_password):
            flash("Password must contain at least one special character!", "danger")
            return redirect(url_for("change_password"))

        connection = get_db_connection()
        cursor = connection.cursor()

        # EMPLOYEE
        if session.get("role") == "employee":

            empid = session.get("empid")

            cursor.execute("""
                SELECT login_pass
                FROM emplogdetails
                WHERE empid = %s
            """, (empid,))

            employee = cursor.fetchone()

            if not employee:
                flash("Employee account not found!", "danger")

            elif employee["login_pass"] != current_password:
                flash("Current password is incorrect!", "danger")

            else:
                cursor.execute("""
                    UPDATE emplogdetails
                    SET login_pass = %s
                    WHERE empid = %s
                """, (new_password, empid))

                connection.commit()

                flash("Password changed successfully!", "success")

                cursor.close()
                connection.close()

                return redirect(url_for("employee_dashboard"))

        # CUSTOMER
        elif session.get("role") == "customer":

            custid = session.get("custid")

            cursor.execute("""
                SELECT Login_pass
                FROM Customerlogdetails
                WHERE Customerid = %s
            """, (custid,))

            customer = cursor.fetchone()

            if not customer:
                flash("Customer account not found!", "danger")

            elif customer["Login_pass"] != current_password:
                flash("Current password is incorrect!", "danger")

            else:
                cursor.execute("""
                    UPDATE Customerlogdetails
                    SET Login_pass = %s
                    WHERE Customerid = %s
                """, (new_password, custid))

                connection.commit()

                flash("Password changed successfully!", "success")

                cursor.close()
                connection.close()

                return redirect(url_for("customer_dashboard"))

        cursor.close()
        connection.close()

    return render_template("change_password.html")


@app.route("/admin/view-employees")
def view_employees():

    if session.get("role") != "admin":
        return redirect(url_for("home"))

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM employee
        JOIN branches USING(branchid)
    """)

    employees = cursor.fetchall()
    cursor.close()
    connection.close()

    return render_template(
        "view_employees.html",
        employees=employees
    )
def employee_dashboard():

    if session.get("role") not in ["employee", "admin"]:
        return redirect(url_for("home"))

    return render_template("employee_dashboard.html")


@app.route("/customer/dashboard")
def customer_dashboard():

    if session.get("role") != "customer":
        return redirect(url_for("home"))

    return render_template("customer_dashboard.html")


@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))

@app.route("/employee/open-account", methods=["GET", "POST"])
def open_account():

    if session.get("role") not in ["employee", "admin"]:
        return redirect(url_for("home"))

    if request.method == "POST":

        name = request.form.get("name").capitalize()
        dob = request.form.get("dob")
        phone = request.form.get("phone")
        email = request.form.get("email")

        accounttype = request.form.get("accounttype").capitalize()
        branchid = request.form.get("branchid")
        balance = request.form.get("balance")

        username = request.form.get("username")
        password = request.form.get("password")

        # Generate account number
        accountnum = r.randrange(10000000, 99999999)

        # Email validation
        email_pattern = re.compile(
            r'^[\w\.-]+@([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$'
        )

        if not email_pattern.match(email):
            flash("Invalid email address!", "danger")
            return redirect(url_for("open_account"))

        # Phone validation
        if not phone.isdigit() or len(phone) != 10:
            flash("Phone number must contain exactly 10 digits!", "danger")
            return redirect(url_for("open_account"))

        # Password validation
        password_pattern = re.compile(
            r'^(?=.*[A-Z])(?=.*[0-9])(?=.*[@$#%^&*()!]).{8,}$'
        )

        if not password_pattern.match(password):
            flash(
                "Password must contain at least 8 characters, "
                "one uppercase letter, one number, and one special character!",
                "danger"
            )
            return redirect(url_for("open_account"))

        connection = get_db_connection()
        cursor = connection.cursor()

        # Check if username already exists
        cursor.execute(
            "SELECT * FROM customerlogdetails WHERE login_id=%s",
            (username,)
        )

        existing_user = cursor.fetchone()

        if existing_user:

            cursor.close()
            connection.close()

            flash("Username already exists!", "danger")
            return redirect(url_for("open_account"))

        # Insert customer
        cursor.execute(
            """
            INSERT INTO customers (name, dob, phone, email)
            VALUES (%s, %s, %s, %s)
            """,
            (name, dob, phone, email)
        )

        connection.commit()

        # Get newly created Customer ID
        custid = cursor.lastrowid

        # Insert account
        cursor.execute(
            """
            INSERT INTO accounts
            (customerid, account_number, account_type, branchid, balance)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (custid, accountnum, accounttype, branchid, balance)
        )

        # Create customer login
        cursor.execute(
            """
            INSERT INTO customerlogdetails
            (customerid, login_id, login_pass)
            VALUES (%s, %s, %s)
            """,
            (custid, username, password)
        )

        connection.commit()

        cursor.close()
        connection.close()

        flash(
            f"Account created successfully! Account Number: {accountnum}",
            "success"
        )

        if session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))
        else:
            return redirect(url_for("employee_dashboard"))

    return render_template("open_account.html")

@app.route("/employee/update-customer", methods=["GET", "POST"])
def update_customer():

    if session.get("role") not in ["employee", "admin"]:
        return redirect(url_for("home"))

    if request.method == "POST":

        customerid = request.form.get("customerid")
        updvar = request.form.get("field")
        value = request.form.get("value")

        # Only allow these columns
        allowed_fields = ["name", "dob", "phone", "email"]

        if updvar not in allowed_fields:
            flash("Invalid field selected!", "danger")
            return redirect(url_for("update_customer"))

        # Phone validation
        if updvar == "phone":

            if not value.isdigit() or len(value) != 10:
                flash(
                    "Phone number must contain exactly 10 digits!",
                    "danger"
                )
                return redirect(url_for("update_customer"))

        # Email validation
        if updvar == "email":

            email_pattern = re.compile(
                r'^[\w\.-]+@([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$'
            )

            if not email_pattern.match(value):
                flash("Invalid email address!", "danger")
                return redirect(url_for("update_customer"))

        connection = get_db_connection()
        cursor = connection.cursor()

        # Check if customer exists
        cursor.execute(
            "SELECT * FROM customers WHERE customerid=%s",
            (customerid,)
        )

        customer = cursor.fetchone()

        if not customer:

            cursor.close()
            connection.close()

            flash("Invalid Customer ID!", "danger")
            return redirect(url_for("update_customer"))

        # Update selected field
        cursor.execute(
            f"UPDATE customers SET {updvar}=%s WHERE customerid=%s",
            (value, customerid)
        )

        connection.commit()

        cursor.close()
        connection.close()

        flash("Customer information updated successfully!", "success")

        if session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))
        else:
            return redirect(url_for("employee_dashboard"))

    return render_template("update_customer.html")

@app.route("/employee/customer-information", methods=["GET", "POST"])
def customer_information():

    if session.get("role") not in ["employee", "admin"]:
        return redirect(url_for("home"))

    customer = None

    if request.method == "POST":

        customerid = request.form.get("customerid")

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT *
            FROM customers
            JOIN accounts USING(customerid)
            JOIN branches USING(branchid)
            WHERE customerid=%s
        """, (customerid,))

        customer = cursor.fetchone()

        cursor.close()
        connection.close()

        if not customer:
            flash("Customer not found!", "danger")

    return render_template(
        "customer_information.html",
        customer=customer
    )

@app.route("/employee/view-customers")
def view_customers():

    if session.get("role") not in ["employee", "admin"]:
        return redirect(url_for("home"))

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM customers
        JOIN accounts USING(customerid)
    """)

    customers = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "view_customers.html",
        customers=customers
    )
@app.route("/employee/close-account", methods=["GET", "POST"])
def close_account():

    if session.get("role") not in ["employee","admin"]:
        return redirect(url_for("home"))

    if request.method == "POST":

        customerid = request.form.get("customerid")

        connection = get_db_connection()
        cursor = connection.cursor()

        # Check if customer exists
        cursor.execute(
            "SELECT * FROM accounts WHERE customerid=%s",
            (customerid,)
        )

        account = cursor.fetchone()

        if not account:
            cursor.close()
            connection.close()

            flash("Invalid Customer ID!", "danger")
            return redirect(url_for("close_account"))

        # Disable account
        cursor.execute(
            """
            UPDATE accounts
            SET account_type='Disabled'
            WHERE customerid=%s
            """,
            (customerid,)
        )

        connection.commit()

        cursor.close()
        connection.close()

        flash("Customer account disabled successfully!", "success")

        if session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))
        else:
            return redirect(url_for("employee_dashboard"))

    return render_template("close_account.html")

@app.route("/employee/update-kyc", methods=["GET", "POST"])
def update_kyc():

    if session.get("role") not in ["employee","admin"]:
        return redirect(url_for("home"))

    if request.method == "POST":

        customerid = request.form.get("customerid")
        account_type = request.form.get("account_type")

        # Validate account type
        if account_type not in ["savings", "current"]:
            flash("Please select a valid account type!", "danger")
            return redirect(url_for("update_kyc"))

        connection = get_db_connection()
        cursor = connection.cursor()

        # Check whether customer/account exists
        cursor.execute(
            "SELECT * FROM accounts WHERE customerid=%s",
            (customerid,)
        )

        account = cursor.fetchone()

        if not account:

            cursor.close()
            connection.close()

            flash("Invalid Customer ID!", "danger")
            return redirect(url_for("update_kyc"))

        # Update account type
        cursor.execute(
            """
            UPDATE accounts
            SET account_type=%s
            WHERE customerid=%s
            """,
            (account_type, customerid)
        )

        connection.commit()

        cursor.close()
        connection.close()

        flash("Customer account updated successfully!", "success")

        if session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))
        else:
            return redirect(url_for("employee_dashboard"))

    return render_template("update_kyc.html")

@app.route("/customer/balance")
def customer_balance():

    if session.get("role") != "customer":
        return redirect(url_for("login"))

    custid = session.get("custid")

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT balance FROM accounts WHERE customerid=%s",
        (custid,)
    )

    balance = cursor.fetchone()

    cursor.close()
    connection.close()

    return render_template(
        "customer_balance.html",
        balance=balance["balance"]
    )

@app.route("/customer/account-details")
def customer_account_details():

    if session.get("role") != "customer":
        return redirect(url_for("login"))

    custid = session.get("custid")

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        "select * from accounts join branches using(branchid) where customerid=%s",
        (custid,)
    )

    account = cursor.fetchone()

    cursor.close()
    connection.close()

    if not account:
        flash("Account details not found!", "danger")
        return redirect(url_for("customer_dashboard"))

    return render_template(
        "customer_account_details.html",
        account=account
    )

@app.route("/customer/deposit", methods=["GET", "POST"])
def customer_deposit():

    if session.get("role") != "customer":
        return redirect(url_for("login"))

    custid = session.get("custid")

    if request.method == "POST":

        depamt = request.form.get("amount")

        # Validate amount
        try:
            depamt = int(depamt)
        except (ValueError, TypeError):
            flash("Please enter a valid amount!", "danger")
            return redirect(url_for("customer_deposit"))

        if depamt <= 0:
            flash("Amount must be greater than 0!", "danger")
            return redirect(url_for("customer_deposit"))

        connection = get_db_connection()
        cursor = connection.cursor()

        # Get account details
        cursor.execute(
            """
            SELECT accountid, balance, account_type
            FROM accounts
            WHERE customerid=%s
            """,
            (custid,)
        )

        account = cursor.fetchone()

        if not account:
            cursor.close()
            connection.close()

            flash("Account not found!", "danger")
            return redirect(url_for("customer_deposit"))

        # Don't allow transactions on disabled account
        if account["account_type"] == "Disabled":
            cursor.close()
            connection.close()

            flash("Your account is disabled!", "danger")
            return redirect(url_for("customer_deposit"))

        new_balance = account["balance"] + depamt

        # Insert transaction
        cursor.execute(
            """
            INSERT INTO transactions
            (accountid, type, amount, date_time, balance_after)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                account["accountid"],
                "deposit",
                depamt,
                dt.datetime.now(),
                new_balance
            )
        )

        connection.commit()

        # Get transaction ID
        cursor.execute(
            """
            SELECT transaction_id
            FROM transactions
            ORDER BY transaction_id DESC
            LIMIT 1
            """
        )

        transaction = cursor.fetchone()

        # Create transaction code
        cursor.execute(
            """
            UPDATE transactions
            SET trx_code=CONCAT('TRX-', transaction_id)
            WHERE transaction_id=%s
            """,
            (transaction["transaction_id"],)
        )

        # Update account balance
        cursor.execute(
            """
            UPDATE accounts
            SET balance=%s
            WHERE customerid=%s
            """,
            (new_balance, custid)
        )

        connection.commit()

        cursor.close()
        connection.close()

        flash(
            f"₹{depamt} deposited successfully!",
            "success"
        )

        return redirect(url_for("customer_deposit"))

    return render_template("customer_deposit.html")

@app.route("/customer/withdraw", methods=["GET", "POST"])
def customer_withdraw():

    if session.get("role") != "customer":
        return redirect(url_for("login"))

    custid = session.get("custid")

    if request.method == "POST":

        wdramt = request.form.get("amount")

        # Validate amount
        try:
            wdramt = int(wdramt)
        except (ValueError, TypeError):
            flash("Please enter a valid amount!", "danger")
            return redirect(url_for("customer_withdraw"))

        if wdramt <= 0:
            flash("Amount must be greater than 0!", "danger")
            return redirect(url_for("customer_withdraw"))

        connection = get_db_connection()
        cursor = connection.cursor()

        # Get account details
        cursor.execute(
            """
            SELECT accountid, balance, account_type
            FROM accounts
            WHERE customerid=%s
            """,
            (custid,)
        )

        account = cursor.fetchone()

        if not account:
            cursor.close()
            connection.close()

            flash("Account not found!", "danger")
            return redirect(url_for("customer_withdraw"))

        # Check account status
        if account["account_type"] == "Disabled":
            cursor.close()
            connection.close()

            flash("Your account is disabled!", "danger")
            return redirect(url_for("customer_withdraw"))

        # Check balance
        if wdramt > account["balance"]:

            cursor.close()
            connection.close()

            flash("Insufficient Balance ❌", "danger")
            return redirect(url_for("customer_withdraw"))

        new_balance = account["balance"] - wdramt

        # Insert transaction
        cursor.execute(
            """
            INSERT INTO transactions
            (accountid, type, amount, date_time, balance_after)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                account["accountid"],
                "withdraw",
                wdramt,
                dt.datetime.now(),
                new_balance
            )
        )

        connection.commit()

        # Get transaction ID
        cursor.execute(
            """
            SELECT transaction_id
            FROM transactions
            ORDER BY transaction_id DESC
            LIMIT 1
            """
        )

        transaction = cursor.fetchone()

        # Generate transaction code
        cursor.execute(
            """
            UPDATE transactions
            SET trx_code=CONCAT('TRX-', transaction_id)
            WHERE transaction_id=%s
            """,
            (transaction["transaction_id"],)
        )

        # Update account balance
        cursor.execute(
            """
            UPDATE accounts
            SET balance=%s
            WHERE customerid=%s
            """,
            (new_balance, custid)
        )

        connection.commit()

        cursor.close()
        connection.close()

        flash(
            f"₹{wdramt} withdrawn successfully!",
            "success"
        )

        return redirect(url_for("customer_withdraw"))

    return render_template("customer_withdraw.html")

@app.route("/customer/transfer", methods=["GET", "POST"])
def customer_transfer():

    if session.get("role") != "customer":
        return redirect(url_for("login"))

    custid = session.get("custid")

    if request.method == "POST":

        raccnumber = request.form.get("account_number")
        trfamt = request.form.get("amount")

        # Validate amount
        try:
            raccnumber = int(raccnumber)
            trfamt = int(trfamt)
        except (ValueError, TypeError):
            flash("Please enter valid details!", "danger")
            return redirect(url_for("customer_transfer"))

        if trfamt <= 0:
            flash("Transfer amount must be greater than 0!", "danger")
            return redirect(url_for("customer_transfer"))

        connection = get_db_connection()
        cursor = connection.cursor()

        # Get sender account
        cursor.execute(
            """
            SELECT accountid, balance, account_type, account_number
            FROM accounts
            WHERE customerid=%s
            """,
            (custid,)
        )

        sender = cursor.fetchone()

        if not sender:
            cursor.close()
            connection.close()

            flash("Your account was not found!", "danger")
            return redirect(url_for("customer_transfer"))

        # Check sender account status
        if sender["account_type"] == "Disabled":
            cursor.close()
            connection.close()

            flash("Your account is disabled!", "danger")
            return redirect(url_for("customer_transfer"))

        # Check sufficient balance
        if trfamt > sender["balance"]:
            cursor.close()
            connection.close()

            flash("Insufficient Balance ❌", "danger")
            return redirect(url_for("customer_transfer"))

        # Check recipient account
        cursor.execute(
            """
            SELECT accountid, balance, account_type, account_number
            FROM accounts
            WHERE account_number=%s
            """,
            (raccnumber,)
        )

        receiver = cursor.fetchone()

        if not receiver:
            cursor.close()
            connection.close()

            flash("Recipient account not found!", "danger")
            return redirect(url_for("customer_transfer"))

        # Prevent transfer to own account
        if receiver["account_number"] == sender["account_number"]:
            cursor.close()
            connection.close()

            flash("You cannot transfer money to your own account!", "danger")
            return redirect(url_for("customer_transfer"))

        # Check receiver account status
        if receiver["account_type"] == "Disabled":
            cursor.close()
            connection.close()

            flash("Recipient account is disabled!", "danger")
            return redirect(url_for("customer_transfer"))

        # Calculate new balances
        sender_balance = sender["balance"] - trfamt
        receiver_balance = receiver["balance"] + trfamt

        # Insert sender transaction
        cursor.execute(
            """
            INSERT INTO transactions
            (
                accountid,
                type,
                amount,
                date_time,
                related_account,
                balance_after
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                sender["accountid"],
                "transfer",
                trfamt,
                dt.datetime.now(),
                raccnumber,
                sender_balance
            )
        )

        connection.commit()

        # Get transaction ID
        cursor.execute(
            """
            SELECT transaction_id
            FROM transactions
            ORDER BY transaction_id DESC
            LIMIT 1
            """
        )

        transaction = cursor.fetchone()

        # Generate transaction code
        cursor.execute(
            """
            UPDATE transactions
            SET trx_code=CONCAT('TRX-', transaction_id)
            WHERE transaction_id=%s
            """,
            (transaction["transaction_id"],)
        )

        # Update sender balance
        cursor.execute(
            """
            UPDATE accounts
            SET balance=%s
            WHERE accountid=%s
            """,
            (
                sender_balance,
                sender["accountid"]
            )
        )

        # Update receiver balance
        cursor.execute(
            """
            UPDATE accounts
            SET balance=%s
            WHERE accountid=%s
            """,
            (
                receiver_balance,
                receiver["accountid"]
            )
        )

        connection.commit()

        cursor.close()
        connection.close()

        flash(
            f"₹{trfamt} sent successfully! ✅",
            "success"
        )

        return redirect(url_for("customer_transfer"))

    return render_template("customer_transfer.html")

@app.route("/customer/transaction-history")
def customer_transaction_history():

    if session.get("role") != "customer":
        return redirect(url_for("login"))

    custid = session.get("custid")

    connection = get_db_connection()
    cursor = connection.cursor()

    # Get account ID
    cursor.execute(
        "SELECT accountid FROM accounts WHERE customerid=%s",
        (custid,)
    )

    account = cursor.fetchone()

    if not account:
        cursor.close()
        connection.close()

        flash("Account not found!", "danger")
        return redirect(url_for("customer_dashboard"))

    accid = account["accountid"]

    # Get transaction history
    cursor.execute(
        """
        SELECT transaction_id,
               type,
               amount,
               date_time,
               related_account
        FROM transactions
        WHERE accountid=%s
        ORDER BY date_time DESC
        """,
        (accid,)
    )

    transactions = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "customer_transaction_history.html",
        transactions=transactions
    )

@app.route("/customer/download-csv")
def customer_download_csv():

    if session.get("role") != "customer":
        return redirect(url_for("login"))

    custid = session.get("custid")

    connection = get_db_connection()
    cursor = connection.cursor()

    # Get account information
    cursor.execute(
        """
        SELECT name,
               account_number,
               account_type,
               balance,
               accountid
        FROM customers
        JOIN accounts
        ON customers.customerid = accounts.customerid
        WHERE customers.customerid=%s
        """,
        (custid,)
    )

    accinfo = cursor.fetchone()

    if not accinfo:
        cursor.close()
        connection.close()

        flash("Account information not found!", "danger")
        return redirect(url_for("customer_transaction_history"))

    accid = accinfo["accountid"]

    # Get transactions
    cursor.execute(
        """
        SELECT transaction_id,
               type,
               amount,
               date_time,
               related_account
        FROM transactions
        WHERE accountid=%s
        ORDER BY date_time DESC
        """,
        (accid,)
    )

    transactions = cursor.fetchall()

    cursor.close()
    connection.close()

    # Create CSV in memory
    output = io.StringIO()

    writer = csv.writer(output)

    # Account information
    writer.writerow([
        "Account Holder Name",
        "Acc Number",
        "Type",
        "Balance"
    ])

    writer.writerow([
        accinfo["name"],
        accinfo["account_number"],
        accinfo["account_type"],
        accinfo["balance"]
    ])

    writer.writerow([])

    # Transaction heading
    writer.writerow([
        "TransactionID",
        "Type",
        "Amount",
        "DateTime",
        "RelatedAccount"
    ])

    # Transaction data
    for transaction in transactions:

        writer.writerow([
            transaction["transaction_id"],
            transaction["type"],
            transaction["amount"],
            transaction["date_time"],
            transaction["related_account"]
        ])

    # Move cursor to beginning
    output.seek(0)

    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name="Statement.csv"
    )

@app.route("/customer/download-pdf")
def customer_download_pdf():

    if session.get("role") != "customer":
        return redirect(url_for("login"))

    custid = session.get("custid")

    connection = get_db_connection()
    cursor = connection.cursor()

    # Get account information
    cursor.execute(
        """
        SELECT name,
               account_number,
               account_type,
               balance,
               accountid
        FROM customers
        JOIN accounts
        ON customers.customerid = accounts.customerid
        WHERE customers.customerid=%s
        """,
        (custid,)
    )

    accinfo = cursor.fetchone()

    if not accinfo:
        cursor.close()
        connection.close()

        flash("Account information not found!", "danger")
        return redirect(url_for("customer_transaction_history"))

    accid = accinfo["accountid"]

    # Get transactions
    cursor.execute(
        """
        SELECT transaction_id,
               type,
               amount,
               date_time,
               related_account
        FROM transactions
        WHERE accountid=%s
        ORDER BY date_time DESC
        """,
        (accid,)
    )

    transactions = cursor.fetchall()

    cursor.close()
    connection.close()

    # Create PDF
    pdf = FPDF()

    pdf.add_page()

    pdf.set_font("Arial", "B", 14)

    pdf.cell(
        0,
        10,
        "BANK STATEMENT",
        ln=True,
        align="C"
    )

    pdf.ln(5)

    # Account information heading
    pdf.set_font("Arial", "B", 11)

    pdf.cell(
        0,
        8,
        "Account Holder Information",
        ln=True
    )

    pdf.ln(2)

    # Account information
    pdf.set_font("Arial", size=10)

    pdf.cell(50, 8, "Account Holder Name:")
    pdf.cell(
        0,
        8,
        str(accinfo["name"]),
        ln=True
    )

    pdf.cell(50, 8, "Account Number:")
    pdf.cell(
        0,
        8,
        str(accinfo["account_number"]),
        ln=True
    )

    pdf.cell(50, 8, "Account Type:")
    pdf.cell(
        0,
        8,
        str(accinfo["account_type"]),
        ln=True
    )

    pdf.cell(50, 8, "Current Balance:")
    pdf.cell(
        0,
        8,
        f"Rs {accinfo['balance']}",
        ln=True
    )

    pdf.ln(6)

    # Transaction table
    headers = [
        "Transaction ID",
        "Type",
        "Amount",
        "Date Time",
        "Related Acc"
    ]

    col_widths = [35, 30, 30, 55, 30]

    row_height = 8

    pdf.set_font("Arial", "B", 9)

    for i, header in enumerate(headers):

        pdf.cell(
            col_widths[i],
            row_height,
            header,
            border=1,
            align="C"
        )

    pdf.ln()

    # Transaction rows
    pdf.set_font("Arial", size=8)

    for transaction in transactions:

        # Add new page if necessary
        if pdf.get_y() > 260:

            pdf.add_page()

            pdf.set_font("Arial", "B", 9)

            for i, header in enumerate(headers):

                pdf.cell(
                    col_widths[i],
                    row_height,
                    header,
                    border=1,
                    align="C"
                )

            pdf.ln()

            pdf.set_font("Arial", size=8)

        values = [
            transaction["transaction_id"],
            transaction["type"],
            transaction["amount"],
            transaction["date_time"],
            transaction["related_account"]
            if transaction["related_account"]
            else "-"
        ]

        for i, value in enumerate(values):

            pdf.cell(
                col_widths[i],
                row_height,
                str(value),
                border=1
            )

        pdf.ln()

    # Save PDF temporarily
    filepath = "Statement.pdf"

    pdf.output(filepath)

    # Send PDF to browser
    return send_file(
        filepath,
        as_attachment=True,
        download_name="Statement.pdf",
        mimetype="application/pdf"
    )


if __name__ == "__main__":
    app.run(debug=True)