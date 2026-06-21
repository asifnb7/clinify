document.addEventListener("DOMContentLoaded", function () {

    const form = document.getElementById("clinify-login-form");

    if (!form) return;

    form.addEventListener("submit", async function(e){

        e.preventDefault();

        const usr = form.querySelector('[name="usr"]').value;
        const pwd = form.querySelector('[name="pwd"]').value;

        try {

            const response = await fetch('/api/method/login', {

                method: 'POST',

                headers: {

                    'Content-Type':'application/x-www-form-urlencoded'

                },

                body:
                    `usr=${encodeURIComponent(usr)}&pwd=${encodeURIComponent(pwd)}`

            });

            const data = await response.json();

            if(data.message==="Logged In"){

                window.location.href =
                    data.home_page || "/app";

            }

        } catch(err){

            alert("Login failed");

            console.error(err);

        }

    });

});
