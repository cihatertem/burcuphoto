let menuBtn = document.querySelector(".nav-button")
let navbar = document.querySelector(".navbar")
let photoList = document.querySelectorAll(".photo-flow-img")
let photoSlider = document.querySelector(".photo-zoom")
let swiperClose = document.querySelector(".btn-swiper-close")
let btnMessage = document.querySelector(".btn-messages")
let messageBox = document.querySelector(".messages")
let checkbox = document.getElementById('checkbox')
let checkboxLabel = document.getElementById("theme-label")
let css = document.getElementById('css')
let navLink = document.getElementsByClassName("nav-link")
let numOne = document.querySelector(".num1")
let numTwo = document.querySelector(".num2")
let captcha = document.querySelector("#captcha")
const submitBtn = document.querySelector("#contact-submit")
const emailForm = document.getElementById("email-form")


//Navlink active
for (let i = 0; i < navLink.length; i++) {
  if (navLink[i].href === window.location.href) {
    navLink[i].classList.add("nav-link-active")
    break
  }
}

//themeswitcher
checkbox.checked = false
let themeValue = localStorage.getItem("theme")
if (themeValue === null) {
  localStorage.setItem('theme', 'dark')
  themeValue = "dark"
}

checkboxLabel.addEventListener('click', e => {
  e.preventDefault()
  if (themeValue === 'dark') {
    css.href = "/static/style/main-light.css"
    localStorage.setItem('theme', 'light')
    checkbox.checked = true
    themeValue = "light"
    return;
  }

  if (themeValue === 'light') {
    css.href = "/static/style/main-dark.css"
    localStorage.setItem('theme', 'dark')
    checkbox.checked = false
    themeValue = "dark"
    return;
  }
})

window.onload = () => {
  let storedTheme = localStorage.getItem('theme')

  if (storedTheme === null || storedTheme === "dark") {
    css.href = "/static/style/main-dark.css"
  }

  if (storedTheme === "light") {
    css.href = "/static/style/main-light.css"
    localStorage.setItem('theme', 'light')
    checkbox.checked = true
  }
}

//Django flash message
if (btnMessage) {
  btnMessage.onclick = e => {
    e.preventDefault()
    messageBox.style.transition = "all .2s linear"
    messageBox.style.right = "-370px"
  }
}

if (messageBox) {
  setTimeout(() => {
    messageBox.style.transition = "all .2s linear"
    messageBox.style.right = "-370px"
  }, 4000)
}

//photo zoom frame
if (swiperClose) {
  swiperClose.onclick = (e) => {
    e.preventDefault()
    photoSlider.classList.toggle("photo-zoom-active")
  }
}

let photoIndex;

for (let i = 0; i < photoList.length; i++) {
  photoList[i].onclick = (e) => {
    e.preventDefault()
    photoSlider.classList.toggle("photo-zoom-active")
    photoIndex = photoList[i].dataset.photoindex - 1
    photoIndex = parseInt(photoIndex)
    const swiper2 = new Swiper('.photo-zoom', {
      rewind: true,
      initialSlide: photoIndex ? photoIndex : 0,
      navigation: {
        nextEl: '.swiper-button-next',
        prevEl: '.swiper-button-prev',
      },
      slidesPerView: 1,
    });
  }

}

// navbar menu-btn
menuBtn.onclick = () => {
  menuBtn.classList.toggle("x-button")
  navbar.classList.toggle("show")

  if (menuBtn.classList.length > 1) {
    menuBtn.innerHTML = "✕"
    menuBtn.style.transform = "rotate(360deg)"
  } else {
    menuBtn.innerHTML = "☰"
    menuBtn.style.transform = "rotate(-360deg)"
  }
}

// portfolio swiper
const swiper1 = new Swiper('.portfolio', {
  loop: true,
  navigation: {
    nextEl: '.swiper-button-next',
    prevEl: '.swiper-button-prev',
  },
  breakpoints: {
    576: {
      slidesPerView: 1,
    },
    786: {
      slidesPerView: document.querySelectorAll('.swiper-slide').length < 2 ?
        document.querySelectorAll('.swiper-slide').length :
        2,
      spaceBetween: 0
    },
    991: {
      slidesPerView: document.querySelectorAll('.swiper-slide').length < 3 ?
        document.querySelectorAll('.swiper-slide').length :
        3,
      spaceBetween: 0
    },
    1200: {
      slidesPerView: document.querySelectorAll('.swiper-slide').length < 4 ?
        document.querySelectorAll('.swiper-slide').length :
        4,
      spaceBetween: 0
    }
  }
});

// CAPTCHA
if (numOne && numTwo) {
  numOne = parseInt(numOne.innerHTML)
  numTwo = parseInt(numTwo.innerHTML)
  let totalNum = numOne + numTwo
  let captchaNum

  captcha.addEventListener("change", e => {
    captchaNum = e.target.value
    captchaNum = parseInt(captchaNum)
    captcha.setCustomValidity("")
  })

  submitBtn.addEventListener("click", e => {
    if (totalNum !== captchaNum) {
      e.preventDefault()
      captcha.setCustomValidity("Your sum is incorrect.\nPlease retry!")
      captcha.reportValidity()
    }
  })


}