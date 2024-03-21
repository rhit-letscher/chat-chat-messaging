from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase

app = Flask(__name__)
app.config["SECRET_KEY"] = "hjhjsdahhds"
socketio = SocketIO(app)

uidToConversation = {"user1": [{"name": "chat1","adminPerms":True},{"name": "chat3","adminPerms":False}]}
rooms = {"chat1": {"members": 1, "messages": [],"type": "public"},"chat2": {"members": 1, "messages": [], "type": "public"}}
uid = "user1"

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
    #default name
    if not name:
        name = uid
        session["name"] = uid

    #for debugging purposes, initializes chatlist if empty
    if(name not in uidToConversation.keys()):
        uidToConversation[name] = []
    else:
        userchats = uidToConversation[name]



    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)
        changename = request.form.get("setname", False)
        
        #if not session["name"]:
        #   return render_template("home.html", error="Please enter a name.", code=code, name=name, userchats=userchats)

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
            rooms[room] = {"members": 0, "messages": [],"type": "public"}
            uidToConversation[session.get("name")].append({"name": room,"adminPerms":True})
            return redirect(url_for("room",id=room))
        
        #session["room"] = room
        #session["name"] = name
        

    return render_template("home.html", userchats=getUserChats(uidToConversation[session.get("name")]))

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
        "message": data["data"]
    }
    send(content, to=room)
    rooms[room]["messages"].append(content)
    print(f"{session.get('name')} said: {data['data']}")

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
        "type": type
    }
    send(content, to=room)

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
        "user": user
    }
    send(content, to=room)
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
            "user": user
            }
            send(content, to=room)
            rooms[room]["messages"].append(content)
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
    send({"name": name, "message": "has entered the room"}, to=room)
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
    
    send({"name": name, "message": "has left the room"}, to=room)
    print(f"{name} has left the room {room}")

if __name__ == "__main__":
    socketio.run(app, debug=True)
