window.dash_clientside = Object.assign({}, window.dash_clientside, {
    clientside: {
        // stopPropagation function removed (if still present)
    }
});

// Use event delegation on the document to handle clicks on dynamic delete buttons
document.addEventListener('click', function(event) {
    // Check if the clicked element or an ancestor matches the delete button class
    const deleteButton = event.target.closest('.gearset-delete-button');

    if (deleteButton) {
        // Stop the click event from propagating further (e.g., to the table row)
        event.stopPropagation();
        // console.log("Delete button click propagation stopped via document listener."); // Optional: for debugging
    }
});
