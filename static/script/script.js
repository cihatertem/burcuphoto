let menuBtn = document.querySelector(".nav-button");
let navbar = document.querySelector(".navbar");
let photoList = document.querySelectorAll(".photo-flow-img");
let photoSlider = document.querySelector(".photo-zoom");
let sliderClose = document.querySelector(".btn-slider-close");
let btnMessage = document.querySelector(".btn-messages");
let messageBox = document.querySelector(".messages");
let checkbox = document.getElementById("checkbox");
let root = document.documentElement;
let navLink = document.getElementsByClassName("nav-link");
let numOne = document.querySelector(".num1");
let numTwo = document.querySelector(".num2");
let captcha = document.querySelector("#captcha");
const submitBtn = document.querySelector("#contact-submit");
const emailForm = document.getElementById("email-form");

//Navlink active
for (let i = 0; i < navLink.length; i++) {
  if (navLink[i].href === window.location.href) {
    navLink[i].classList.add("nav-link-active");
    break;
  }
}

//themeswitcher
const setTheme = (theme) => {
  root.dataset.theme = theme;
  checkbox.checked = theme === "light";
  localStorage.setItem("theme", theme);
};

const getPreferredTheme = () => {
  const storedTheme = localStorage.getItem("theme");
  if (storedTheme) {
    return storedTheme;
  }

  if (window.matchMedia?.("(prefers-color-scheme: light)").matches) {
    return "light";
  }

  return "dark";
};

checkbox.checked = false;
addEventListener("DOMContentLoaded", () => {
  setTheme(getPreferredTheme());
});

checkbox.addEventListener("change", () => {
  setTheme(checkbox.checked ? "light" : "dark");
});

//Django flash message
if (btnMessage) {
  btnMessage.onclick = (e) => {
    e.preventDefault();
    messageBox.style.transition = "all .2s linear";
    messageBox.style.right = "-370px";
  };
}

if (messageBox) {
  setTimeout(() => {
    messageBox.style.transition = "all .2s linear";
    messageBox.style.right = "-370px";
  }, 4000);
}

//photo zoom frame
if (sliderClose) {
  sliderClose.onclick = (e) => {
    e.preventDefault();
    photoSlider.classList.remove("photo-zoom-active");
  };
}

let photoIndex;
let slider2 = null;

for (let i = 0; i < photoList.length; i++) {
  photoList[i].onclick = (e) => {
    e.preventDefault();
    photoSlider.classList.add("photo-zoom-active");
    
    photoIndex = parseInt(photoList[i].dataset.photoindex || 1) - 1;
    if (isNaN(photoIndex) || photoIndex < 0) photoIndex = 0;

    if (!slider2) {
      slider2 = new VanillaSlider(".photo-zoom", {
        loop: true,
        initialSlide: photoIndex,
        navigation: {
          nextEl: ".slider-button-next",
          prevEl: ".slider-button-prev",
        },
        slidesPerView: 1,
      });
    } else {
      slider2.goTo(photoIndex, false);
    }
  };
}

// navbar menu-btn
menuBtn.onclick = () => {
  menuBtn.classList.toggle("x-button");
  navbar.classList.toggle("show");

  if (menuBtn.classList.length > 1) {
    menuBtn.innerHTML = "✕";
    menuBtn.style.transform = "rotate(360deg)";
  } else {
    menuBtn.innerHTML = "☰";
    menuBtn.style.transform = "rotate(-360deg)";
  }
};

// portfolio slider
const slideCount = document.querySelectorAll(".portfolio .slider-slide").length;
const slider1 = new VanillaSlider(".portfolio", {
  loop: true,
  direction : 'horizontal',
  slidesPerView: 4,
  spaceBetween: 0,
  navigation: {
    nextEl: ".slider-button-next",
    prevEl: ".slider-button-prev",
  },
  breakpoints: {
    200: {
      slidesPerView: 1,
      spaceBetween: 0
    },
    576: {
      slidesPerView: 1,
      spaceBetween: 0
    },
    786: {
      slidesPerView: slideCount < 2 ? slideCount : 2,
      spaceBetween: 0,
    },
    991: {
      slidesPerView: slideCount < 3 ? slideCount : 3,
      spaceBetween: 0,
    },
    1200: {
      slidesPerView: slideCount < 4 ? slideCount : 4,
      spaceBetween: 0,
    },
  },
});

// CAPTCHA
if (numOne && numTwo) {
  numOne = parseInt(numOne.innerHTML);
  numTwo = parseInt(numTwo.innerHTML);
  let totalNum = numOne + numTwo;
  let captchaNum;

  captcha.addEventListener("keyup", (e) => {
    captchaNum = e.target.value;
    captchaNum = parseInt(captchaNum);
    captcha.setCustomValidity("");
  });

  submitBtn.addEventListener("click", (e) => {
    if (totalNum !== captchaNum) {
      e.preventDefault();
      captcha.setCustomValidity("Your sum is incorrect.\nPlease retry!");
      captcha.reportValidity();
    }
  });
}
