from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = ("j8t-dqu1Vr[b_L5-")

def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY NOT NULL,
            username TEXT NOT NULL,
            mdp TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS friends (
            user_id TEXT NOT NULL,
            friend_id TEXT NOT NULL,
            PRIMARY KEY (user_id, friend_id),
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (friend_id) REFERENCES users (id),
            CHECK (user_id <> friend_id)
        )
    """)
    conn.commit()
    conn.close()

@app.route("/")
def index():
    friends = []
    user_id = session.get("id")

    if user_id is not None:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT friend_id FROM friends WHERE user_id = ?",
                (user_id,),
            )
            friends = [friend_id for (friend_id,) in cursor.fetchall()]
        finally:
            conn.close()
    return render_template(
        "index.html",
        username=session.get("username"),
        friends=friends
    )

@app.route("/stats")
def stats():
    pass

@app.route("/friends")
def friends_page():
    user_id = session.get("id")
    if user_id is None:
        return redirect(url_for("login"))

    return render_template(
        "friends.html",
        friends=get_friends(user_id),
    )

def get_friends(user_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT users.id, users.username
            FROM friends
            JOIN users ON users.id = friends.friend_id
            WHERE friends.user_id = ?
            ORDER BY users.username
            """,
            (user_id,),
        )
        friends = cursor.fetchall()
    finally:
        conn.close()

    return friends

@app.route("/add-friend", methods=["POST"])
def ajouter_ami():
    user_id = session.get("id")
    if user_id is None:
        return redirect(url_for("login"))

    friend_id = request.form.get("friend_id", "").strip()
    erreur = None

    if not friend_id:
        erreur = "Saisis l'identifiant de la personne à ajouter."
    elif friend_id == user_id:
        erreur = "Tu ne peux pas t'ajouter toi-même."
    else:
        connection = get_db_connection()
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT 1 FROM users WHERE id = ?", (friend_id,))
            if cursor.fetchone() is None:
                error = "Aucun compte ne correspond à cet identifiant."
            else:
                try:
                    cursor.execute(
                        "INSERT INTO friends (user_id, friend_id) VALUES (?, ?)",
                        (user_id, friend_id),
                    )
                    connection.commit()
                    return redirect(url_for("friends_page"))
                except sqlite3.IntegrityError:
                    erreur = "Cette personne est déjà dans ta liste d'amis."
        finally:
            connection.close()

    return render_template(
        "friends.html",
        friends=get_friends(user_id),
        error=erreur,
    )

@app.route("/register", methods=["GET", "POST"])
def register():
  if request.method == "POST":
    user_id = request.form["id"]
    username = request.form["username"]
    password = request.form["mdp"]
    hashed_password = generate_password_hash(password)

    try:
      conn = get_db_connection()
      cursor = conn.cursor()
      cursor.execute(
          "INSERT INTO users (id, username, mdp) VALUES (?, ?, ?)",
          (user_id, username, hashed_password),
      )
      conn.commit()
      conn.close()
      return redirect(url_for("login"))
    except sqlite3.IntegrityError:
      return "Ce nom d'utilisateur existe déjà !"

  return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
  if request.method == "POST":
    user_id = request.form["id"]
    password = request.form["mdp"]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT mdp, username FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user[0], password):
      session["id"] = user_id
      session["username"] = user[1]
      return redirect(url_for("index"))
    else:
      return "Identifiant ou mot de passe incorrect."

  return render_template("login.html")

@app.route("/logout")
def logout():
  session.clear()
  return redirect(url_for("index"))

if __name__ == "__main__":
  init_db()
  app.run(host="0.0.0.0", port=5000, debug=True)
