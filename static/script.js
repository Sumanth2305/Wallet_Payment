document.addEventListener('DOMContentLoaded', () => {
    const mainContent = document.getElementById('main-content');

    // Handle Send Money button click
    document.getElementById('send-money-btn')?.addEventListener('click', () => {
        mainContent.innerHTML = `
            <h2>Send Money</h2>
            <form id="send-money-form" action="/send_money" method="POST">
                <label for="recipient">Recipient (Email/Phone):</label>
                <input type="text" id="recipient" name="recipient" required>
                <label for="amount">Amount:</label>
                <input type="number" id="amount" name="amount" required>
                <button type="submit">Send</button>
            </form>
        `;
        
        // Add form submission listener (if needed for validation)
        document.getElementById('send-money-form')?.addEventListener('submit', (event) => {
            event.preventDefault(); // Prevent the default form submission behavior
            
            const recipient = document.getElementById('recipient').value;
            const amount = document.getElementById('amount').value;
            
            if (!recipient || !amount) {
                alert('Please fill in both fields.');
                return;
            }

            // Submit the form via Fetch or AJAX if needed
            const formData = new FormData(document.getElementById('send-money-form'));
            
            fetch('/send_money', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Money sent successfully!');
                } else {
                    alert('Error: ' + data.message);
                }
            })
            .catch(err => alert('Error: ' + err));
        });
    });

    // Handle Request Money button click
    document.getElementById('request-money-btn')?.addEventListener('click', () => {
        mainContent.innerHTML = `
            <h2>Request Money</h2>
            <form id="request-money-form" action="/request_money" method="POST">
                <label for="requester">Requester (Email/Phone):</label>
                <input type="text" id="requester" name="requester" required>
                <label for="request-amount">Amount:</label>
                <input type="number" id="request-amount" name="request-amount" required>
                <button type="submit">Request</button>
            </form>
        `;
        
        // Add form submission listener (if needed for validation)
        document.getElementById('request-money-form')?.addEventListener('submit', (event) => {
            event.preventDefault(); // Prevent the default form submission behavior

            const requester = document.getElementById('requester').value;
            const amount = document.getElementById('request-amount').value;
            
            if (!requester || !amount) {
                alert('Please fill in both fields.');
                return;
            }

            // Submit the form via Fetch or AJAX if needed
            const formData = new FormData(document.getElementById('request-money-form'));

            fetch('/request_money', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Money requested successfully!');
                } else {
                    alert('Error: ' + data.message);
                }
            })
            .catch(err => alert('Error: ' + err));
        });
    });

    // Handle Statements button click
    document.getElementById('statements-btn')?.addEventListener('click', () => {
        mainContent.innerHTML = `
            <h2>Transaction Statements</h2>
            <p>Here you can view your transaction statements.</p>
            <button id="view-statements-btn">View Statements</button>
        `;
        
        // Add event listener to the button to handle the redirect
        document.getElementById('view-statements-btn')?.addEventListener('click', () => {
            window.location.href = '/statements'; // Redirect to the Flask route for statements
        });
    });

    // Additional functionalities can be added here if necessary
});
