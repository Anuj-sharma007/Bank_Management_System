import pymysql
import smtplib
import random as r
import re 
import datetime as dt
import csv
from tabulate import tabulate
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from fpdf import FPDF

dbcon = pymysql.connect(host='localhost', user= 'root', password='anuj2025', database='bankdb')
dbcon

mycursor=dbcon.cursor()

def admin_authentication():
    user=input("Enter user name::")
    passw=input("Enter password::")
    if user=="root" and passw=="anuj2025":
        print("Login Successfull✅")
        while True:
            admchoice=input("1.Register Employee\n2.Delete Employee \n3.See All Employees\n4.Exit")
            if admchoice in ["1","2","3"]:
                admin(admchoice)
            else:
                break
    else:
        print("Invalid ")
        admin_authentication()
    

def emp_authentication():
    empid=input("Enter Employee ID")
    empusername=input("Enter Username")
    emppass=input("Enter Login Password")
    if mycursor.execute("select login_id,login_pass,empid from emplogdetails where login_id=%s and login_pass=%s and empid=%s",\
                        (empusername,emppass,empid))!=0:
        print("Login Successfull✅")
        while True:
            op=input("1.Open account \n2.Update Customer Details  \n3.See Customer Information \n4.See All Customers \n5.Close Account \n6.Update KYC\n7.Exit\n")
            if op in ["1","2","3","4","5","6"]:
                emp_func(op)
            else:
                break
    else:
        print("Invalid EmployeeID or Login  Details❌")
        emp_authentication()

def cust_authentication():
    custid=input("Enter Customer ID")
    custusername=input("Enter User Name")
    custpass=input("Enter Login Password")
    if mycursor.execute("select customerid,login_id,login_pass from customerlogdetails where customerid=%s and login_id=%s and login_pass=%s",\
                        (custid,custusername,custpass))!=0:
            print("Login Successful✅")
            cust_func(custid)
    else:
        print("Invalid CustomerID or Login Details❌")
        cust_authentication()

def validate_email():
    email=input("Enter email id::")
    pattern=re.compile('^[\w\.-]+@([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$')
    if not pattern.match(email):
        print("Enter valid email id")
        validate_email()
    else:
        return email

def validate_phone():
    phone=input("Enter phone number::")
    if len(phone)==10:
        return phone
    else:
        validate_phone()

def validate_date():
    date=input("Enter date of birth in YYYY-MM-DD format::")
    try:
        dt.datetime.strptime(date, "%Y-%m-%d")
        return date
    except ValueError:
        validate_date()


def admin(admchoice):
    if admchoice=="1":
        name=input("Enter Employee name::").capitalize()
        dob=validate_date()
        phone=validate_phone()
        email=validate_email()
        salary=int(input("Enter the salary::"))
        branchid=int(input("Enter branch id::"))
        while True:
            username = input("Create username::")
            if mycursor.execute("select * from emplogdetails where login_id=%s",(username))!=0:
                print(f"{username} is already exist")
            else:
                print(f"{username} is available")
                password = input(f"Enter the password\n1.password should contain atleast 1 Uppercase, special char,digit and 8 character long")
                pattern = re.compile('^(?=.*[A-Z])(?=.*[0-9])(?=.*[@$#%^&*()!]).{8,}$')
                if not pattern.match(password):
                    print("Invalid password❌")
                else:
                    print("Registered Sucessfully✅")
                    break
        mycursor.execute("insert into employee (name,dob,phone,email,salary,branchid) \
                values(%s,%s,%s,%s,%s,%s)",(name,dob,phone,email,salary,branchid))
        dbcon.commit()
        mycursor.execute("select empid from employee order by empid desc limit 1")
        for ele in mycursor.fetchall():
            empid=ele[0]
        mycursor.execute("INSERT INTO emplogdetails VALUES (%s, %s,%s)", (username,password,empid))
        dbcon.commit()
    elif admchoice=="2":
        delid=int(input("Enter the employee id to update"))
        if mycursor.execute("select * from employee where empid=%s",delid)!=0:            
            mycursor.execute("update employee set emp_status='Former' where empid=%s",delid)
            dbcon.commit()
            print("Updated Successfully✅")
        else:
            print("Invalid Employee ID")
    elif admchoice=="3":
        mycursor.execute("select * from employee join branches using(branchid)")
        rows=mycursor.fetchall()
        print(tabulate(rows, headers=[desc[0] for desc in mycursor.description], tablefmt="simple grid"))
        
    
       

def emp_func(op):
    if op=="1":
        name=input("Enter the customer name::").capitalize()
        dob=validate_date()
        phone=validate_phone()
        email=validate_email()
        mycursor.execute("insert into customers(name,dob,phone,email) values(%s,%s,%s,%s)",\
                         (name,dob,phone,email))
        dbcon.commit()
        accounttype=input("Enter type of account (savings/current)::").capitalize()
        accountnum=r.randrange(10000000,99999999)
        branchid=input("Enter branch of account::")
        balance=input("Enter balance of account::")
        mycursor.execute("select customerid from customers order by  customerid desc limit 1")
        for ele in mycursor.fetchall():
            custid=ele[0]
        print("Create Userid and Password")
        while True:
            username = input("Create username::")
            if mycursor.execute("select * from customerlogdetails where login_id=%s",(username))!=0:
                print(f"{username} is already exist")
            else:
                print(f"{username} is available")
                password = input(f"Enter the password\n1.password should contain atleast 1 Uppercase, special char,digit and 8 character long")
                pattern = re.compile('^(?=.*[A-Z])(?=.*[0-9])(?=.*[@$#%^&*()!]).{8,}$')
                if not pattern.match(password):
                    print("Invalid password❌")
                else:
                    break
        mycursor.execute("insert into accounts(customerid,account_number,account_type,branchid,balance) values(%s,%s,%s,%s,%s)",\
            (custid,accountnum,accounttype,branchid,balance))
        mycursor.execute("insert into customerlogdetails(customerid,login_id,login_pass) values(%s,%s,%s)",(custid,username,password))      
        dbcon.commit()
        print("Account Created Successfully✅")
        
    elif op=="2":
        ucustid=int(input("Enter the customer id for update")) 
        updvar=input("1.Name 2.DoB 3.Phone 4.Email ").lower()
        value=input("Enter new info")
        if updvar in ["name","email","dob"]:
            mycursor.execute(f"update customers set {updvar}=%s where customerid=%s",(value,ucustid))
            dbcon.commit()
        elif updvar in ["phone"]:
            value=int(value)
            mycursor.execute(f"update customers set {updvar}=%s where customerid=%s",(value,ucustid))
            dbcon.commit()
        else:
            print("Invalid option")
    elif op=="3":
        vcustid=input("Enter the customer id to view::")
        mycursor.execute("select * from customers join accounts using(customerid) join branches using(branchid) where customerid=%s",vcustid)
        row=mycursor.fetchone()
        print(f"""
                    -----------------------------------------
                            CUSTOMER ACCOUNT DETAILS
                    -----------------------------------------
                            Branch ID       : {row[0]}
                            Customer ID     : {row[1]}
                            Name            : {row[2]}
                            DoB             : {row[3]}
                            Phone           : {row[4]}
                            Email           : {row[5]}
                            Account ID      : {row[6]}
                            Account Number  : {row[7]}
                            Account Type    : {row[8]}
                            Balance         : {row[9]}
                            Branch Name     : {row[10]}
                            Branch State    : {row[11]}
                            
                    -----------------------------------------
                                    """)
    elif op=="4":
        mycursor.execute("select * from customers join accounts using(customerid)")
        rows=mycursor.fetchall()
        print(tabulate(rows, headers=[desc[0] for desc in mycursor.description], tablefmt="simple grid"))
    elif op=="5":
        closingid=input("Enter the customer id to close account")
        mycursor.execute("update accounts set account_type='Disabled' where customerid=%s",closingid)
        dbcon.commit()
        print("Account Disabled Successfully✅")
    elif op=="6":
        upid=input("Enter the customer id to update account status")
        mycursor.execute("update accounts set account_type='savings' where customerid=%s",upid)
        dbcon.commit()
        print("Done✅")
    else:
        print("Invalid Option")
        
    

def deposit(custid):
    mycursor.execute("select accountid,balance from accounts where customerid=%s",custid)
    row=mycursor.fetchone()
    depamt=int(input("Enter the amount you want to deposit"))
    mycursor.execute("insert into transactions(accountid,type,amount,date_time,balance_after) values(%s,%s,%s,%s,%s)",\
                         (row[0],"deposit",depamt,dt.datetime.now(),row[1]+depamt))
    dbcon.commit()
    mycursor.execute("select transaction_id from transactions order by transaction_id desc limit 1")
    tr=mycursor.fetchone()
    mycursor.execute("update transactions set trx_code=concat('TRX-',transaction_id) where transaction_id=%s",tr[0])
    dbcon.commit()
    mycursor.execute("update accounts set balance=%s where customerid=%s",(row[1]+depamt,custid))
    dbcon.commit()
    print("Deposited Successfully✅")
    

def withdraw(custid):
    mycursor.execute("select accountid,balance from accounts where customerid=%s",custid)
    row=mycursor.fetchone()
    wdramt=int(input("Enter the amount you want to deposit"))
    if wdramt<row[1]:
        mycursor.execute("insert into transactions(accountid,type,amount,date_time,balance_after) values(%s,%s,%s,%s,%s)",\
                         (row[0],"withdraw",wdramt,dt.datetime.now(),row[1]-wdramt))
        dbcon.commit()
        mycursor.execute("select transaction_id from transactions order by transaction_id desc limit 1")
        tr=mycursor.fetchone()
        mycursor.execute("update transactions set trx_code=concat('TRX-',transaction_id) where transaction_id=%s",tr[0])
        dbcon.commit()
        mycursor.execute("update accounts set balance=%s where customerid=%s",(row[1]-wdramt,custid))
        dbcon.commit()
        print("Withdraw Successfull✅")
    else:
        print("Insufficint Balance❌")

def transfer(custid):
    mycursor.execute("select accountid,balance from accounts where customerid=%s",custid)
    row=mycursor.fetchone()
    raccnumber=int(input("Enter the account number to which you want to send money"))
    trfamt=int(input("Enter the amount"))
    if trfamt<row[1]:
        mycursor.execute("select accountid,balance from accounts where account_number=%s",raccnumber)
        rdetails=mycursor.fetchone()
        mycursor.execute("insert into transactions(accountid,type,amount,date_time,related_account,balance_after) values(%s,%s,%s,%s,%s,%s)",\
                         (row[0],"transfer",trfamt,dt.datetime.now(),raccnumber,row[1]-trfamt))
        dbcon.commit()
        mycursor.execute("select transaction_id from transactions order by transaction_id desc limit 1")
        tr=mycursor.fetchone()
        mycursor.execute("update transactions set trx_code=concat('TRX-',transaction_id) where transaction_id=%s",tr[0])
        dbcon.commit()
        mycursor.execute("update accounts set balance=%s where customerid=%s",(row[1]-trfamt,custid))
        mycursor.execute("update accounts set balance=%s where accountid=%s",(rdetails[1]+trfamt,rdetails[0]))
        dbcon.commit()
        print("Sent Successfully✅")
    else:
        print("Insufficient Balance❌")
    

def csv_download(accid):
    mycursor.execute("select name,account_number,account_type,balance FROM customers\
    JOIN accounts ON customers.customerid = accounts.customerid where accountid=%s",accid)
    accinfo=mycursor.fetchone()
    lst=[("Account Holder Name","Acc Number","Type","Balance",),accinfo,("","","",""),("TransactionID","Type","Amount","DateTime","RelatedAccount")]
    mycursor.execute("select transaction_id,type,amount,date_time,related_account from transactions where accountid=%s",accid)
    for ele in mycursor.fetchall():
        lst.append(ele)
    with open("Statement.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(lst)
    print("Downloaded")
    

def pdf_download(accid):
    mycursor.execute("select name,account_number,account_type,balance FROM customers\
    JOIN accounts ON customers.customerid = accounts.customerid where accountid=%s",accid)
    accinfo=mycursor.fetchone()
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "BANK STATEMENT", ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "Account Holder Information", ln=True)
    pdf.ln(2)

    pdf.set_font("Arial", size=10)
    
    pdf.cell(50, 8, "Account Holder Name:")
    pdf.cell(0, 8, accinfo[0], ln=True)
    
    pdf.cell(50, 8, "Account Number:")
    pdf.cell(0, 8, str(accinfo[1]), ln=True)
    
    pdf.cell(50, 8, "Account Type:")
    pdf.cell(0, 8, accinfo[2], ln=True)
    
    pdf.cell(50, 8, "Current Balance:")
    pdf.cell(0, 8, f"Rs{accinfo[3]}", ln=True)
    pdf.ln(6)

    x = pdf.get_x()
    y = pdf.get_y()
    pdf.rect(10, y - 48, 180, 45)

    
        #pdf.add_page()
    mycursor.execute("select transaction_id,type,amount,date_time,related_account from transactions where accountid=%s",accid)
    rows=mycursor.fetchall()
    headers = ["Transaction ID", "Type", "Amount", "Date Time", "Related Acc"]
    col_widths = [40, 30, 30, 50, 30]  # date, type, amount, balance, remarks
    row_height = 8
    pdf.set_font("Arial", "B", 10)
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], row_height, header, border=1, align='C')
    pdf.ln()
    pdf.set_font("Arial", size=9)
    for row in rows:

        if pdf.get_y() > 260:
            pdf.add_page()

            pdf.set_font("Arial", "B", 10)
            for i, h in enumerate(headers):
                pdf.cell(col_widths[i], row_height, h, border=1, align="C")
            pdf.ln()
            pdf.set_font("Arial", size=9)

        for i, col in enumerate(row):
            pdf.cell(col_widths[i], row_height, str(col), border=1)

        pdf.ln()

    pdf.output("Statement.pdf")
    print("Downloaded")
    

def transaction_history(custid):
    mycursor.execute("select accountid from accounts where customerid=%s",custid)
    for ele in mycursor.fetchall():
        accid=ele[0]
    mycursor.execute("select transaction_id,type,amount,date_time,related_account from transactions where accountid=%s",accid)
    rows=mycursor.fetchall()
    print(tabulate(rows, headers=[desc[0] for desc in mycursor.description], tablefmt="heavy_grid"))
    download=input("Download Statement (CSV:1/PDF:2)")
    if download=="1":
        csv_download(accid)
    elif download=="2":
        pdf_download(accid)
    else:
        print("Choose valid option")
    

def cust_func(custid):
    while True:
        choice=input("1.See Account Balance \n2.See Account Details \n3.Deposit Money \n4.Withdraw Money\
        \n5.Transfer Money \n6.Transaction History \n7.Exit")
        
        if choice=="1":
            mycursor.execute("select balance from accounts where customerid=%s",custid)
            bal=mycursor.fetchone()
            print(f"Available Balance:₹{bal[0]}")
        elif choice=="2":
            mycursor.execute("select * from accounts where customerid=%s",custid)
            row=mycursor.fetchone()
            print(f"""
                        -----------------------------------------
                                CUSTOMER ACCOUNT DETAILS
                        -----------------------------------------
                                Account ID      : {row[0]}
                                Customer ID     : {row[1]}
                                Account Number  : {row[2]}
                                Account Type    : {row[3]}
                                Branch ID       : {row[4]}
                                Balance         : ₹{row[5]}
                        -----------------------------------------
                                        """)
        elif choice=="3":
            deposit(custid)

        elif choice=="4":
            withdraw(custid)

        elif choice=="5":
            transfer(custid)
        elif choice=="6":
            transaction_history(custid)

        else:
            break

while True:
    print("-"*50)
    print("🏦HDFC ONLINE BANKING🏦".center(50))
    print("-"*50)
    profile=input("Enter Your Profile \n1.Admin\n2.Employee\n3.Customer\n4.Exit").lower()
    if profile=="1":
        admin_authentication()
    elif profile=="2":
        emp_authentication() 
    elif profile=="3":
        cust_authentication()
    elif profile=="4":
        print("Closing...")
        break
    else:
        print("❌Invalid Option❌")

dbcon.close()

