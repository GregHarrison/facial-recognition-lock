var server_port = 65432;
var server_addr = "192.168.86.31";   // the IP address of your Raspberry Pi
var isLocked = 1;  // Track status of lock
var name; //the name of an authorized user


function userAuthorized(name) {
    // Display greeting to user
    document.getElementById("message").innerHTML = "Hi " + name + "!";

    // Change button text to locked
    document.getElementById("lock").innerHTML = "Click to Unlock";

    // Enable the button to be clicked
    if (document.getElementById("lock").classList.contains("disabled")) {
        document.getElementById("lock").classList.remove("disabled");
    }
}


function client() {
    
    const net = require('net');

    const client = net.createConnection({ port: server_port, host: server_addr }, () => {
        // 'connect' listener.
        console.log('connected to server!');
        
        // send the message
        client.write(JSON.stringify({
            isLocked: isLocked
        }));
    });
    
    // get the data from the server
    client.on('data', (data) => {
        data = JSON.parse(data); // parse data received
        name = data.name;

        if (data.name) {
            userAuthorized(data.name)
        }

        console.log(data.toString());
        client.end();
        client.destroy();
    });

    client.on('end', () => {
        console.log('disconnected from server');
    });
}

update_data()

/* update data for every 1800ms. This needs to be larger than the referesh rate of the camera
so that it is the time limiting factor or else there will be a delay between when the button 
is pressed and the lock status is changed */
function update_data() {
    setInterval(function() {
        // get image from python server
        client();
    }, 1800);
}


function lockUnlock() {
    
    // if locked, unlock. If unlocked, lock
    isLocked ? isLocked = 0 : isLocked = 1;

    // Update page appropriately
    setLockStatus(isLocked)
}

function setLockStatus(isLocked) {
    
    // If lock is currently locked
    if (isLocked) {
        // Change color to red to signify the lock is locked and disable the button
        // The lock may not be unlocked until the authorized user's face is recognized again
        var lock = document.getElementById("lock").classList;
        if (lock.contains("btn-success")) {
            lock.remove("btn-success");
        }
        lock.add("btn-danger");
        lock.add("disabled");
        
        // Change button text to locked
        document.getElementById("lock").innerHTML = "Locked"; 
        
        // Change lock status text
        document.getElementById('lockStatus').innerHTML = "Current Status: Locked";

        // Clear the greeting message to the authorized user
        document.getElementById('message').innerHTML = ""

    } 
    // If lock is unlocked
    else { 
        
        var lock = document.getElementById("lock").classList;
        // Change color to green to signify that the lock is unlocked
        if (lock.contains("btn-danger")) {
            lock.remove("btn-danger");
        }
        lock.add("btn-success");
        
        // Change button text
        document.getElementById("lock").innerHTML = "Click to Lock"; 

        // Change lock status text
        document.getElementById('lockStatus').innerHTML = "Current Status: Unlocked";

    }
}


// Update the screen with the current status of the lock
window.onload = function() {
    setLockStatus(isLocked);
}