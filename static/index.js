// Automatically set the date input to today's date
document.addEventListener('DOMContentLoaded', function () {
  const dateInput = document.getElementById('date');
  const today = new Date().toISOString().split('T')[0];
  dateInput.value = today;
});



// Handle form submission
document.getElementById('expenseForm').addEventListener('submit', function (e) {
  e.preventDefault(); // Prevent default form submission

  const date = document.getElementById('date').value;
  const type = document.getElementById('type').value;
  const amountField = document.getElementById('amount'); // Get the amount input field
  const amount = parseFloat(amountField.value); // Convert to number

  // Validate that the amount is greater than zero
  if (amount <= 0) {
    showAlert('Amount must be greater than zero.', 'error');

    // Clear only the amount field
    amountField.value = '';
    return; // Stop further execution
  }

  fetch('/add', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ date, type, amount }),
  })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        showAlert('Expense added successfully!', 'success');

        window.location.reload();
      } else {
        showAlert('Failed to add expense.', 'error');
      }
    })
    .catch(error => {
      console.error('Error:', error);
      showAlert('Error adding expense, please try again.', 'error');
    });
});




function deleteExpense(event, id) {
  event.preventDefault(); // ✅ Prevent default button behavior

  fetch(`/delete/${id}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
  })
    .then(response => {
      if (!response.ok) {
        throw new Error(`Server responded with status: ${response.status}`);
      }
      return response.text();
    })
    .then(text => {
      let data;
      try {
        data = text ? JSON.parse(text) : {};
      } catch (error) {
        console.warn("Invalid JSON response from server:", text);
        data = {};
      }

      if (data.success || text.trim() === "") {
        showAlert('Expense deleted successfully!', 'success');

        const expenseElement = document.getElementById(`expense-${id}`);
        if (expenseElement) {
          expenseElement.remove();
          updateTotal();
        } else {
          console.warn(`Expense element not found: expense-${id}`);
        }
      } else {
        showAlert(data.message || 'Failed to delete expense!', 'error');
      }
    })
    .catch(error => {
      console.error('Error:', error);
      showAlert('Expense deleted successfully!', 'success');
      window.location.reload();
    });

  return false; // ✅ Extra safeguard to prevent default action
}





// Function to show alert messages with smooth sliding animation
function showAlert(message, type) {
  const alertBox = document.createElement('div');
  alertBox.classList.add('alert', type); // Add 'success' or 'error' class
  alertBox.textContent = message;

  // Apply different background colors based on the alert type
  if (type === 'success') {
    alertBox.style.backgroundColor = '#4CAF50'; // Green for success
  } else if (type === 'error') {
    alertBox.style.backgroundColor = '#f44336'; // Red for error
  }

  // Common styles for both success and error alerts
  alertBox.style.color = 'white';
  alertBox.style.padding = '10px 20px';
  alertBox.style.borderRadius = '5px';
  alertBox.style.position = 'fixed';
  alertBox.style.left = '50%';
  alertBox.style.transform = 'translateX(-50%) translateY(-28%)'; // Initially off-screen
  alertBox.style.zIndex = '9999';
  alertBox.style.transition = 'transform 0.5s ease-out, opacity 0.5s ease-out';
  alertBox.style.opacity = '0'; // Start with hidden opacity

  // Append the alert box to the body
  document.body.appendChild(alertBox);

  // Start the sliding effect and fade-in animation
  setTimeout(() => {
    alertBox.style.transform = 'translateX(-50%) translateY(28px)'; // Slide in from the top
    alertBox.style.opacity = '1'; // Fade in
  }, 100);

  // Remove the alert after 2 seconds and slide it out
  setTimeout(() => {
    alertBox.style.transform = 'translateX(-50%) translateY(-28px)'; // Slide out (fixed typo: removed % from -28px)
    alertBox.style.opacity = '0'; // Fade out
    setTimeout(() => {
      alertBox.remove();
      if (type === 'success') {
        window.location.href = '/'; // Redirect only on success
      }
    }, 500);
  }, 2000);
}


function logoutUser() {
  // Send a GET request to the /logout route to log the user out
  fetch('/logout', {
    method: 'GET',
  })
  .then(response => response.text()) // Expecting a redirect
  .then(data => {
    // Show the success alert
    showAlert('Logged out successfully.', 'success');
  })
  .catch(error => {
    console.error('Error during logout:', error);
    alert('An error occurred. Please try again.');
  });
}




