"use strict";
const ImageSlider = () => {
  let images = ["../static/img/image3.jpg", "../static/img/image4.jpg"];
  let imageIndex = 0;
  let header = document.querySelector("header");
  setInterval(() => {
    imageIndex += 1;
    if (imageIndex >= images.length) {
      imageIndex = 0;
    }
    header.style.backgroundImage = `url(${images[imageIndex]})`;
  }, 3000);
};

ImageSlider();

document.addEventListener("DOMContentLoaded", function () {
  const destinationInput = document.getElementById("destinationInput");
  const destinationSuggestions = document.getElementById("destinationSuggestions");
  let destinations = [];
  let selectedSuggestion = null;
  let suggestionSelected = false;
  let isTyping = false;

  destinationInput.addEventListener("input", function () {
    const inputValue = this.value.trim().toLowerCase();
    if (inputValue.length === 0) {
      destinationSuggestions.style.display = "none";
      return;
    }

    const filteredDestinations = destinations.filter((destination) =>
      destination.toLowerCase().includes(inputValue)
    );
    populateSuggestions(filteredDestinations);
    isTyping = true;
  });

  destinationSuggestions.addEventListener("click", function (event) {
    if (event.target.tagName === "LI") {
      destinationInput.value = event.target.textContent;
      selectedSuggestion = event.target;
      suggestionSelected = true;
      destinationSuggestions.style.display = "none"; // Hide suggestions
      destinationInput.focus(); // Focus back on the input field
    }
  });

  destinationInput.addEventListener("keydown", function (event) {
    const suggestions = destinationSuggestions.querySelectorAll("li");
    const selectedIndex = Array.from(suggestions).indexOf(selectedSuggestion);

    if (event.key === "ArrowDown") {
      event.preventDefault(); // Prevent scrolling
      if (selectedIndex < suggestions.length - 1) {
        selectedSuggestion = suggestions[selectedIndex + 1];
        highlightSelectedSuggestion();
      }
    } else if (event.key === "ArrowUp") {
      event.preventDefault(); // Prevent scrolling
      if (selectedIndex > 0) {
        selectedSuggestion = suggestions[selectedIndex - 1];
        highlightSelectedSuggestion();
      }
    } else if (event.key === "Tab" && suggestionSelected) {
      suggestionSelected = false;
      return; // Allow default tab behavior after suggestion is selected
    } else if (event.key === "Tab" && !suggestionSelected) {
      event.preventDefault(); // Prevent default tab behavior until suggestion is selected
    }
  });

  destinationInput.addEventListener("blur", function () {
    if (!suggestionSelected && !isTyping) {
      destinationInput.value = ""; // Clear input if suggestion not selected and not typing
    }
    suggestionSelected = false;
    isTyping = false;
    // Focus on the next input field when the destination input loses focus
    const nextInput = destinationInput.nextElementSibling;
    if (nextInput) {
      nextInput.focus();
    }
  });

  fetch("../static/js/dataset_cities.csv")
    .then((response) => response.text())
    .then((data) => {
      // Split CSV data into rows
      const rows = data.split("\n");

      // Extract header row to identify the index of the "Place Name" field
      const headers = rows[0].split(",");
      const placeNameIndex = headers.indexOf("Place Name");

      // Populate destinations array with unique destination names
      for (let i = 1; i < rows.length; i++) {
        const columns = rows[i].split(",");
        const placeName = columns[placeNameIndex].trim();
        if (placeName && !destinations.includes(placeName)) {
          destinations.push(placeName);
        }
      }
    })
    .catch((error) => {
      console.error("Error fetching destinations:", error);
    });

  function populateSuggestions(suggestions) {
    if (suggestions.length === 0 || !isTyping) {
      destinationSuggestions.style.display = "none";
      return;
    }

    destinationSuggestions.innerHTML = "";
    suggestions.forEach((suggestion) => {
      const li = document.createElement("li");
      li.textContent = suggestion.replace(/"/g, ""); // Remove double quotes
      destinationSuggestions.appendChild(li);
    });
    destinationSuggestions.style.display = "block"; // Show suggestions
    selectedSuggestion = destinationSuggestions.querySelector("li");
    highlightSelectedSuggestion();
  }

  function highlightSelectedSuggestion() {
    const suggestions = destinationSuggestions.querySelectorAll("li");
    suggestions.forEach((suggestion) => {
      if (suggestion === selectedSuggestion) {
        suggestion.classList.add("selected");
      } else {
        suggestion.classList.remove("selected");
      }
    });
  }
});
