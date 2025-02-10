// script.js
document.getElementById('payment-form').addEventListener('submit', function(event) {
    event.preventDefault();

    const transactionId = document.getElementById('transaction-id').value.trim();
    const statusMessage = document.getElementById('status-message');

    if (transactionId === '') {
        statusMessage.textContent = 'Please enter a valid Transaction ID.';
        statusMessage.style.color = 'red';
        return;
    }

    // Simulated payment validation
    statusMessage.textContent = 'Validating payment...';
    statusMessage.style.color = '#00796b';

    setTimeout(() => {
        if (transactionId === '123456') {  // Example valid ID
            statusMessage.textContent = 'Payment Successful ✅';
            statusMessage.style.color = 'green';
        } else {
            statusMessage.textContent = 'Payment Failed ❌. Invalid Transaction ID.';
            statusMessage.style.color = 'red';
        }
    }, 2000);
});
