# Elevator
An django based elevator system

**Project Setup**

Please Follow the below steps to setup the django project:

clone this repository (advised to do it in a seperate virtual environment)

In the main project app run the following command to install all dependencies pip install -r requirements.txt

setup a local Postgres database and user grant with all priviledges on that database to the user (assuming postgres is installed in your local else run sudo apt install postgresql postgresql-contrib to install)

once postgres is setup and db and user are created run the following commands in the main project app the following command:

python manage.py migrate

create a super user for you django admin by python manage.py createsuperuser and follow the instructions.

Now your repository is setup


**Business Logic for Elvator System**

According to me a good elevator system reflects 2 important criterias :
1. When a user request for an elevator he/she gets an elevator assigned which would reach them as sooner as possible
2. At some point of time all the users in the elevator should reach their destination floors.

I have considered these 2 important factors in the business logic for implementing The elevator system.

Before starting with the logic i would like to inform you about the entities and their possible states:
So there are total 3 entities or models in this system 
**Firstly** the system itself,it has attributes of number of elevators in the system a system is initiated once , door status of an elevato i.e open or close.
**Secondly** An elevator, there are 2 states of an elevator 1. Idle (elevator is at halt) 2. Going Up (elevator is currently going up 3. Going down simlarly.
**Thirdly** A request a request is specific to an elevator and it too has 3 states 
1. Active (the elevator is assiged and the user is waiting for the elevator to board
2. Boarded (user has boarded the elevator and will soon reach the destination 
3. Fuflilled (this request was fulfilled )

The Logic goes like this :
**For Assigning an elevator to a request:**
We want to assign the elevator nearest the user.
So three cases arise 
1. If elevator is at the same floor where user is present (ovious case user will board that) so this elevator is assigned to the user. if more than one elevator is at the same floorthe one which has least requests will be assigned.
2. For user to reach faster to their destinations we need to equally split requests across all elevators possible so that one elevator is not havin 10 requests for a same floor and some elevator is idle.
3. If we have elevators only above or only below its fine we will assign the one which is closest and again if multiple are there we will take the one with least requests.
4. In case there are elevators above and below at at this point we dont know where this user will be going so we get the nearest elevator below which is going up and nearest elevator above and comming down which ever is nerest we assign it.

I understand the above logic might not be always optimal in real case but this will gaurantee that user is allocated an elevator and it is the one which is nearest to him at that point.
So the above logic fullfills the criteria 1 for an good elevator design.

Now lets look at how we ensure crietria 2 for a good system i.e it full fills all the requests assigned to it in  optimal way.

**For moving elevator and fulfilling requests**
The idea implemented here is that whenever an elavator is moving up we keep it moving in same direction until there is someone toboard to elevator at above floors or someone will de board the elevator at some above floor.
Similarly whenever the elevator is going down we keep going dwn until we users to board or deboard at below floor.

Again this might cause in some cases where some users who have boarded the elevator before others and have to wait longer to deboard compared to other user but this will ensure that anyone who has booarded will be taken to his destination floor.

Now i will add below the api endpoints their impact and purpose and their respective methods and payloads for basic understanding .

For reference https://www.postman.com/ayushr20s/workspace/elevator/collection/18804740-0e076161-be83-4650-906b-1567e005f525?action=share&creator=18804740 is the postman api collection

1. http://127.0.0.1:8000/api/elevatorsystem/ -> APi to create an eleator system with n elevators (Note onlty Get and post method is allowed for this modelviewset api
   Method - post
   payload {
    "name": "system 1",
    "elevators_count": 3,
    "max_floors": 10
  }
  Response - {
    "id": 8,
    "name": "system 1",
    "elevators_count": 3,
    "max_floors": 10
}

2. http://127.0.0.1:8000/api/elevator/request-elevator  --> this will create a user request and assign an elevator for thsi request.
   Method = Post
   payload - {
    "pick_up_floor": 2
  }
  Response - {
    "id": 58,
    "pick_up_floor": 2,
    "destination_floor": null,
    "status": "Active",
    "elevator": 6 // this is the elevator assigned to this request as per above logic
  }

3. http://127.0.0.1:8000/api/elevator/3/get-active-requests  --> Returns list of all requests which are in active/Boarded state for an elevator
   Method - Get
   Response [
    {
        "id": 58,
        "pick_up_floor": 2,
        "destination_floor": null,
        "status": "Active",
        "elevator": 6
    }
]

4. http://127.0.0.1:8000/api/elevator/6/open-close-doors --> will open the door of elevator if door was closed else if open then close it
   Method : Patch (only)
   Response - {
    "door_status": "Open"
  }

5. http://127.0.0.1:8000/api/elevator/6/move-elevator --> This will move the elevator with id 6 to its next floor validation for elevator under maintainance or no request or door status open is raised accordingly
   Method - Patch (only)
   Response - {
    "id": 6,
    "current_floor": 2,
    "next_floor": null, // this means no further requests 
    "is_under_maintainance": false,
    "door_status": "Closed",
    "elevator_status": "Going_up",
    "system": 8
  }

6. http://127.0.0.1:8000/api/elevator/6/next-floor --> this api will give the next floor of the elevator at that moment Note the next floor in move elevator api response might be outdated if a request for same eleavtor is added which might change it.
   Method - Get
   response {
   "next_floor" - 3
   }

7. http://127.0.0.1:8000/api/elevator/7/under-maintainance --> Marks the elevator for under maintainance . At this point we mark all the requests of that elevator in statuis boarded or active as fulfilled and user can again request for an elevator from here
  Method - PAtch (only)
   response {
    "id": 7,
    "current_floor": 0,
    "next_floor": null,
    "is_under_maintainance": true,
    "door_status": "Closed",
    "elevator_status": "Idle",
    "system": 8
}

8. http://127.0.0.1:8000/api/elevator/request-elevator/106/  --> user adds their destination floor NOTE this is mandatory for every user to choose their destination floor at the time of boarding else elevator will not move .
   Method - PUT
   payload {
    "destination_floor": 9
}

response -- {
    "destination_floor": 9
}
