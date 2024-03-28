from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase
from datetime import datetime

app = Flask(__name__)
app.config["SECRET_KEY"] = "hjhjahds"
socketio = SocketIO(app)

numReports = [0]
globalAdmins = ["user1","admin"]
reports = [{"reportID":0,"CID":"room","datetime":"sample","dateReported":"sample","messageContent":"sample","reportedUser":"sample","submittedBy":"sample","status":"PENDING"}]
users = {"user1": "password","admin":"adminadmin"}
uidToConversation = {"user1": [{"name": "chat1","adminPerms":True},{"name": "chat3","adminPerms":False}],"admin": [{"name": "chat3","adminPerms":True}]}
rooms = {"chat1": {"members": 1, "messages": [],"type": "public","msgCount":0},"chat3": {"members": 1, "messages": [], "type": "public","msgCount":0}}
uid = "user1"

def getActiveReports():
    activereports = []
    for report in reports:
        if(report["status"]=="PENDING"):
            activereports.append(report)
    print(activereports)
    return activereports

def getRedactedReports():
    redacted = []
    for report in reports:
        if(report["status"]=="REDACTED"):
            redacted.append(report)
    return redacted

def getDismissedReports():
    dismissed = []
    for report in reports:
        if(report["status"]=="DISMISSED"):
            dismissed.append(report)
    return dismissed

def getReportByID(id):
    for report in reports:
        if(report["reportID"]==id):
            return report

def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)
        
        if code not in rooms:
            break
    
    return code

def getChatMembers(chatName):
    members = []
    for user in uidToConversation.keys():
        for chat in uidToConversation[user]:
            if(chat["name"] == chatName):
                members.append(user)
    return members

def getUserChats(chatInfo):
    print(chatInfo)
    namelist = []
    for conversation in chatInfo:
        namelist.append(conversation["name"])
    print(namelist)
    return namelist

def isRoomAdmin(user,roomName):
    for room in uidToConversation[user]:
        if(room["name"] == roomName):
            return room["adminPerms"]


@app.route("/", methods=["POST", "GET"])
def home():
    name = session.get("name")
    print(session.get("name"))
    #default name
    if not name:
        return redirect(url_for("login"))

    #for debugging purposes, initializes chatlist if empty
    if(name not in uidToConversation.keys()):
        return redirect(url_for("login"))
    else:
        userchats = uidToConversation[name]


    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)
        changename = request.form.get("setname", False)
        logout = request.form.get("logout", False)
        
        #if not session["name"]:
        #   return render_template("home.html", error="Please enter a name.", code=code, name=name, userchats=userchats)

        #logout
        if logout != False:
            print("clicked logout")
            session.clear()
            session["message"] = "Logout successful."
            return redirect(url_for("login"))

        #join room
        if join != False:
            print("clicked join")
            if not code:
                return render_template("home.html", error="Please enter a room code.", code=code, name=session.get("name"), userchats=getUserChats(uidToConversation[session.get("name")]))
            elif code not in rooms:
                return render_template("home.html", error="Room does not exist.", code=code, name=session.get("name"), userchats=getUserChats(uidToConversation[session.get("name")]))
            elif (rooms[code]["type"] == "private" and session.get("name") not in getChatMembers(code)):
                return render_template("home.html", error="Cannot join private room.", code=code, name=session.get("name"), userchats=getUserChats(uidToConversation[session.get("name")]))
            else:
                uidToConversation[session.get("name")].append({"name": code,"adminPerms":False})
                return redirect(url_for("room",id=code))

        #change name
        if changename != False:
            print("clicked namechange")
            session["name"] = name
            if(name not in uidToConversation.keys()):
                uidToConversation[name] = []
        
        #room = code
        if create != False:
            print("clicked create")
            room = generate_unique_code(4)
            rooms[room] = {"members": 0, "messages": [],"type": "public", "msgCount":0}
            uidToConversation[session.get("name")].append({"name": room,"adminPerms":True})
            return redirect(url_for("room",id=room))
        
        #session["room"] = room
        #session["name"] = name
        

    return render_template("home.html", name=session.get("name"),userchats=getUserChats(uidToConversation[session.get("name")]))

@app.route("/admin")
def adminpanel():
    if session.get("name") not in globalAdmins:
        return redirect(url_for("/"))
    return render_template("admin.html",reports=reports)

@app.route("/register",methods=["POST", "GET"])
def register():
    if request.method == "POST":
        allowedChars = set(c for c in '0123456789a...zA...Z~!@#$%^&*()_+')
        username = request.form.get("username")
        password = request.form.get("password")
        if password is None or username is None:
            return
        if username in users.keys():
            return render_template("register.html",error="Error: User already exists. Please choose a new username.");
        if len(password)<8:
            return render_template("register.html",error="Error: Password must be at least 8 characters long.");
        #if any(userChar not in allowedChars for userChar in username):
        #    return render_template("register.html",error="Error: Username must only contain alphanumeric characters or the symbols ~!@#$%^&*()_+");
        #if any(passChar not in allowedChars for passChar in password):
        #    return render_template("register.html",error="Error: Password must only contain alphanumeric characters or the symbols ~!@#$%^&*()_+");
        #init tables. todo: replace with dbms
        users[username] = password
        uidToConversation[username] = []
        print(f"registering {username}")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login",methods=["POST", "GET"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        print(f"attempting login {username}")
        print(list(users.keys()))
        if username not in list(users.keys()):
            return render_template("login.html", error="User does not exist.")
        if users[username] != password:
            return render_template("login.html", error="Incorrect password.")
        session['name'] = username
        print("login successful, redirecting")
        return redirect(url_for("home"))
    return render_template("login.html")

    

@app.route("/room")
def room():
    #room = session.get("room")
    room = request.args.get('id')
    session['room'] = room
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("home"))

    return render_template("room.html", code=room, messages=rooms[room]["messages"], members=getChatMembers(room),isAdmin = isRoomAdmin(session.get("name"),room),uid=session.get("name"),type=rooms[room]["type"])

@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in rooms:
        return 
    
    content = {
        "name": session.get("name"),
        "message": data["data"],
        "date": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "id":rooms[room]["msgCount"]+1
    }
    send(content, to=room)
    rooms[room]["messages"].append(content)
    rooms[room]["msgCount"] = rooms[room]["msgCount"] + 1
    print(f"{session.get('name')} said: {data['data']}")
    print(f"at {content['date']}")

@socketio.on("setType")
def setType(type):
    if type not in ["public","private"]:
        return
    room = session.get("room")
    admin = session.get("name")
    if room not in rooms:
        return 
    if not isRoomAdmin(admin,room):
        print("error: invalid perms")
        return
    rooms[room]["type"] = type
    content = {
        "name": "System",
        "message": f"{admin} has changed conversation type to {type}",
        "changeType": "true",
        "type": type,
        "date": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "id":rooms[room]["msgCount"]+1
    }
    rooms[room]["msgCount"] = rooms[room]["msgCount"]+1
    send(content, to=room)

@socketio.on("dismissMessage")
def dismissMessage(reportID):
    print("got it")
    print(reportID)
    report = getReportByID(reportID)
    report["status"] = "DISMISSED"

@socketio.on("redactMessage")
def redactMessage(reportID):
    print("got it")
    print(reportID)
    report = getReportByID(reportID)
    report["status"] = "REDACTED"
    CID = report["CID"]
    sender = report["reportedUser"]
    datetime = report["datetime"]
    roomMsgs=rooms[CID]["messages"]
    for message in roomMsgs:
        if(message["name"] == sender and message["date"] == datetime):
            print("found message")
            message["message"] = "<b>This message has been redacted by our moderation team due to violating our content policy.</b>"
    rooms[CID]["messages"] = roomMsgs
    print(reports)

@socketio.on("sendReport")
def sendReport(msg):
    print("report received")
    submittedBy = session.get("name")
    CID = session.get("room")
    message = msg["content"]
    messageDate = msg["date"]
    print(submittedBy)
    print(message)
    print(CID)
    messageContent = ""
    reportedUser = ""
    split = False
    for i in range(len(message)):
        if(not split):
            if (message[i] == ':'):
               split = True
            else:
                reportedUser += message[i]
        else:
            messageContent+= message[i]
    
    numReports[0] = numReports[0] + 1
    report = {"reportID":numReports[0],
                    "CID":CID,
                    "datetime":messageDate,
                    "dateReported": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    "messageContent":messageContent,
                    "reportedUser":reportedUser,
                    "submittedBy":submittedBy,
                    "status":"PENDING"}
    reports.append(report)
    print(reports)

@socketio.on("addMember")
def addMember(user):
    user = user['user']
    print("adding member  "+user)
    room = session.get("room")
    admin = session.get("name")
    if room not in rooms:
        return 
    if not isRoomAdmin(admin,room):
        print("error: invalid perms")
        return
    print(uidToConversation.keys())
    if user not in uidToConversation.keys():
        print("error invalid username")
        return
        #todo: return error invalid username to client 
    print(uidToConversation[user])
    uidToConversation[user].append({"name": room, "adminPerms": False})
    print(uidToConversation[user])
    content = {
        "name": "System",
        "message": f"{admin} has added {user} to the room",
        "addUser": "true",
        "user": user,
        "date": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "id":rooms[room]["msgCount"]+1
    }
    send(content, to=room)
    rooms[room]["msgCount"] = rooms[room]["msgCount"]+1
    rooms[room]["messages"].append(content)

@socketio.on("removeMember")
def removeMember(user):
    user = user['user']
    print("removing user "+user)
    print(uidToConversation[user])
    room = session.get("room")
    admin = session.get("name")
    if room not in rooms:
        return 
    if not isRoomAdmin(admin,room):
        print("error: invalid perms")
        return
    if user not in uidToConversation.keys():
        print("error invalid username")
        return
        #todo: return error invalid username to client 
    for i in range(len(uidToConversation[user])):
        print(uidToConversation[user][i]['name'])
        print(room)
        if uidToConversation[user][i]['name'] == room:
            print("found room!!")
            del uidToConversation[user][i]
            print("deleting user "+user)
            content = {
            "name": "System",
            "message": f"{admin} has removed {user} from the room",
            "removeUser": "true",
            "user": user,
            "date": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "id": rooms[room]["msgCount"]+ 1
            }
            send(content, to=room)
            rooms[room]["messages"].append(content)
            rooms[room]["msgCount"] = rooms[room]["msgCount"] + 1
            break

@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return
    if rooms[room]["type"] != "public":
        return render_template("home.html", error="This room is private.", code=room, name=session.get("name"), userchats=getUserChats(uidToConversation[session.get("name")]))
    
    join_room(room)
    send({"name": name, "message": "has entered the room","date": datetime.now().strftime("%d/%m/%Y %H:%M:%S")}, to=room)
    rooms[room]["members"] += 1
    print(f"{name} joined room {room}")

@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -= 1
        #if rooms[room]["members"] <= 0:
        #    del rooms[room] s
    
    send({"name": name, "message": "has left the room","date": datetime.now().strftime("%d/%m/%Y %H:%M:%S")}, to=room)
    print(f"{name} has left the room {room}")

if __name__ == "__main__":
    socketio.run(app, debug=True)
