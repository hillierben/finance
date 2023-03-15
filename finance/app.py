import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """Show portfolio of stocks"""
    id = session["user_id"]

    if (db.execute("SELECT SUM(amount) FROM purchases WHERE user_id = ?", id)[0]["SUM(amount)"]) == None:
        return render_template("index.html")

    index = db.execute("SELECT user_id, stock_id, name, SUM(shares) FROM purchases GROUP BY stock_id")

    i = 0
    for crab in index:
        amounts = usd(float(db.execute("SELECT SUM(amount) FROM purchases GROUP BY stock_id")[i]["SUM(amount)"]))
        i += 1
        crab["amount"] = amounts

    cash = db.execute("SELECT cash FROM users WHERE id = ?", id)
    cashUSD = usd(cash[0]["cash"])

    totalAmount = usd(float(db.execute("SELECT SUM(amount) FROM purchases WHERE user_id = ?", id)
                            [0]["SUM(amount)"]) + float(cash[0]["cash"]))

    return render_template("index.html", index=index, amount=amounts, cash=cashUSD, total=totalAmount)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template("buy.html")

    if request.method == "POST":
        if request.form.get("symbol") == "":
            return apology("Stock doesn't exist")
        elif request.form.get("symbol").isalpha() == False:
            return apology("Stock doesn't exist")
        elif request.form.get("shares") == "":
            return apology("Enter amount of Shares")
        elif request.form.get("shares").isnumeric() == False:
            return apology("Only enter NUMBER of shares")

        # Check current stock amount

        dict = lookup(request.form.get("symbol"))
        if dict:
            amount = float(dict["price"]) * float(request.form.get("shares"))
            name = dict["name"]
        # Check user has enough in their account
            userCash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
            userCashRemain = float(userCash[0]["cash"]) - float(amount)
            if userCashRemain >= 0:
                db.execute("UPDATE users SET cash = ? WHERE id = ?", userCashRemain, session["user_id"])
                db.execute("INSERT INTO purchases(user_id, stock_id, name, shares, amount) VALUES(?, ?, ?, ?, ?)",
                           session["user_id"], request.form.get("symbol"), name, request.form.get("shares"), amount)
            else:
                return apology("Insufficient Funds")

            return redirect("/")

        else:
            return apology("Stock does not exist")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    history = db.execute("SELECT * FROM purchases WHERE user_id = ?", session["user_id"])
    print(history)

    return render_template("history.html", history=history)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/", 200)

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "GET":
        return render_template("quote.html")

    dict = {}
    if (lookup(request.form.get("symbol"))) == None:
        return apology("Stock does not exist")
    else:
        dict = lookup(request.form.get("symbol"))

        return render_template("quoted.html", name=dict["name"], price=usd(dict["price"]))


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        if (request.form.get("username") == "" or request.form.get("password") == "" or request.form.get("confirmation") == ""):
            return apology("Please fill in all fields")
        if (request.form.get("password") != request.form.get("confirmation")):
            return apology("Passwords don't match")

        username = request.form.get("username")
        password = request.form.get("password")

        checkName = db.execute("SELECT username FROM users WHERE username = ?", username)

        if checkName:
            if username in checkName[0].values():
                return apology("Username already exists")

        hash = generate_password_hash(password, method="pbkdf2:sha256", salt_length=8)

        db.execute("INSERT INTO users(username, hash) VALUES(?, ?)", username, hash)

        return redirect("/")

    return render_template("/register.html")


@app.route("/funds", methods=["POST"])
@login_required
def addFunds():
    fundAmount = request.form.get("fundAmount")
    print(fundAmount)
    totalFund = float(db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]) + float(fundAmount)
    db.execute("UPDATE users SET cash = ? WHERE id = ?", totalFund, session["user_id"])

    return render_template("/buy.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    # check for GET
    if request.method == "GET":
        tempStock = db.execute("SELECT DISTINCT(stock_id) FROM purchases WHERE user_id = ?", session["user_id"])
        return render_template("sell.html", stock=tempStock)
        # get list of bought stocks

    # if symbol doesn't exist
    if lookup(request.form.get("symbol")) == None or request.form.get("symbol") == "":
        return apology("Stock doesn't exist")

    # if shares field is empty
    if request.form.get("shares") == "":
        return apology("Please enter shares you wish to sell")

    # check for negative shares
    if int(request.form.get("shares")) <= 0:
        return apology("No negative shares, please!")

    # if user does not own stock
    if not db.execute("SELECT stock_id FROM purchases WHERE stock_id = ? AND user_id = ?", request.form.get("symbol"), session["user_id"]):
        return apology("You do not own this stock")

    # if user doesn't own enough stock
    if (db.execute("SELECT SUM(shares) FROM purchases WHERE stock_id = ?", request.form.get("symbol")))[0]["SUM(shares)"] < int(request.form.get("shares")):
        return apology("You do not own this amount of stock")

    # if user is selling all stock, delete from database
    if (db.execute("SELECT SUM(shares) FROM purchases WHERE stock_id = ?", request.form.get("symbol")))[0]["SUM(shares)"] == int(request.form.get("shares")):
        db.execute("DELETE FROM purchases WHERE stock_id = ?", request.form.get("symbol"))

    if (db.execute("SELECT SUM(shares) FROM purchases WHERE stock_id = ?", request.form.get("symbol")))[0]["SUM(shares)"] > int(request.form.get("shares")):
        tempStock = -1 * (int(request.form.get("shares")))
        tempAmount = -1 * ((lookup(request.form.get("symbol"))["price"]) * (float(request.form.get("shares"))))
        print(tempStock)
        print(tempAmount)
        db.execute("INSERT INTO purchases(user_id, stock_id, name, shares, amount) VALUES(?, ?, ?, ?, ?)",
                   session["user_id"], request.form.get("symbol"), lookup(request.form.get("symbol"))["name"], tempStock, tempAmount)

    return redirect("/")
