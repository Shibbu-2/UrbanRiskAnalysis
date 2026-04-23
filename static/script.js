// ---------------- FORM VALIDATION ----------------

function validateForm(){

let temp=document.getElementById("temp").value;
let humidity=document.getElementById("humidity").value;
let aqi=document.getElementById("aqi").value;
let rain=document.getElementById("rain").value;
let pop=document.getElementById("pop").value;

if(temp=="" || humidity=="" || aqi=="" || rain=="" || pop==""){
alert("Please fill all fields");
return false;
}

if(isNaN(temp) || isNaN(humidity) || isNaN(aqi) || isNaN(rain) || isNaN(pop)){
alert("Enter numeric values only");
return false;
}

return true;

}

function sendMessage(){

let input=document.getElementById("userInput");
let message=input.value.trim();

if(message==="") return;

let chatbox=document.getElementById("chatbox");

chatbox.innerHTML += "<div class='user'>"+message+"</div>";

fetch("/chatbot",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({message:message})
})

.then(response=>response.json())

.then(data=>{

chatbox.innerHTML += "<div class='bot'>"+data.reply+"</div>";

chatbox.scrollTop = chatbox.scrollHeight;

});

input.value="";
}

document.getElementById("userInput").addEventListener("keypress", function(event){

if(event.key==="Enter"){
sendMessage();
}

});