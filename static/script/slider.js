class VanillaSlider {
    constructor(selector, options = {}) {
        this.container = typeof selector === 'string' ? document.querySelector(selector) : selector;
        if (!this.container) return;

        this.wrapper = this.container.querySelector('.slider-wrapper');
        this.originalSlides = Array.from(this.wrapper.children);
        this.slides = [...this.originalSlides];
        this.nextBtn = this.container.querySelector('.slider-button-next');
        this.prevBtn = this.container.querySelector('.slider-button-prev');
        
        this.options = Object.assign({
            loop: false,
            initialSlide: 0,
            slidesPerView: 1,
            breakpoints: {}
        }, options);

        this.currentSlidesPerView = this.options.slidesPerView;
        this.currentIndex = this.options.initialSlide;

        // Swipe variables
        this.startX = 0;
        this.currentX = 0;
        this.isDragging = false;
        this.moved = false;
        this.isTransitioning = false;
        this.loopInitialized = false;

        this.init();
    }

    init() {
        this.updateBreakpoints();

        window.addEventListener('resize', () => {
            this.updateBreakpoints();
            this.updatePosition(false);
        });

        if (this.nextBtn) {
            this.nextBtn.addEventListener('click', (e) => {
                e.preventDefault();
                if (!this.isTransitioning) this.next();
            });
        }
        if (this.prevBtn) {
            this.prevBtn.addEventListener('click', (e) => {
                e.preventDefault();
                if (!this.isTransitioning) this.prev();
            });
        }
        
        this.wrapper.addEventListener('transitionend', () => {
            this.isTransitioning = false;
            if (this.options.loop) this.checkLoop();
        });

        // Touch events
        this.wrapper.addEventListener('touchstart', this.touchStart.bind(this), {passive: true});
        this.wrapper.addEventListener('touchmove', this.touchMove.bind(this), {passive: true});
        this.wrapper.addEventListener('touchend', this.touchEnd.bind(this));
        
        this.wrapper.addEventListener('mousedown', this.touchStart.bind(this));
        this.wrapper.addEventListener('mousemove', this.touchMove.bind(this));
        this.wrapper.addEventListener('mouseup', this.touchEnd.bind(this));
        this.wrapper.addEventListener('mouseleave', this.touchEnd.bind(this));

        this.wrapper.addEventListener('click', (e) => {
            if (this.moved) {
                e.preventDefault();
                e.stopPropagation();
                this.moved = false;
            }
        }, { capture: true });

        this.updateSlides();
        this.updatePosition(false);
        this.checkDisabled();
    }

    setupLoop() {
        // Remove old clones
        this.wrapper.querySelectorAll('.slider-clone').forEach(el => el.remove());
        this.slides = [...this.originalSlides];

        // Only loop if we have more original slides than slidesPerView
        if (this.originalSlides.length <= this.currentSlidesPerView) return;

        const clonesBefore = [];
        const clonesAfter = [];
        
        for (let i = 0; i < this.currentSlidesPerView; i++) {
            const cloneB = this.originalSlides[this.originalSlides.length - 1 - i].cloneNode(true);
            cloneB.classList.add('slider-clone');
            clonesBefore.unshift(cloneB);

            const cloneA = this.originalSlides[i].cloneNode(true);
            cloneA.classList.add('slider-clone');
            clonesAfter.push(cloneA);
        }

        clonesBefore.forEach(clone => this.wrapper.insertBefore(clone, this.wrapper.firstChild));
        clonesAfter.forEach(clone => this.wrapper.appendChild(clone));

        this.slides = Array.from(this.wrapper.children);
        
        if (!this.loopInitialized) {
            this.currentIndex += this.currentSlidesPerView;
            this.loopInitialized = true;
        }
    }

    checkLoop() {
        if (!this.options.loop || this.originalSlides.length <= this.currentSlidesPerView) return;

        if (this.currentIndex < this.currentSlidesPerView) {
            this.currentIndex += this.originalSlides.length;
            this.updatePosition(false);
        } else if (this.currentIndex >= this.originalSlides.length + this.currentSlidesPerView) {
            this.currentIndex -= this.originalSlides.length;
            this.updatePosition(false);
        }
    }

    checkDisabled() {
        const disabled = this.originalSlides.length <= this.currentSlidesPerView;
        if (disabled) {
            this.container.classList.add('slider-disabled');
            if (this.nextBtn) this.nextBtn.style.display = 'none';
            if (this.prevBtn) this.prevBtn.style.display = 'none';
            
            // Snap back to 0 so we don't end up on a blank screen
            if (!this.options.loop || disabled) {
                 this.currentIndex = 0;
            }
            this.updatePosition(false);
        } else {
            this.container.classList.remove('slider-disabled');
            if (this.nextBtn) this.nextBtn.style.display = '';
            if (this.prevBtn) this.prevBtn.style.display = '';
        }
        return disabled;
    }

    touchStart(event) {
        if (this.isTransitioning || this.checkDisabled()) return;
        this.isDragging = true;
        this.moved = false;
        this.startX = this.getPositionX(event);
        this.currentX = this.startX;
        this.wrapper.style.transition = 'none';
    }

    touchMove(event) {
        if (!this.isDragging) return;
        this.currentX = this.getPositionX(event);
        const diff = this.currentX - this.startX;
        
        if (Math.abs(diff) > 5) {
            this.moved = true;
        }

        const currentOffset = -(this.currentIndex * (100 / this.currentSlidesPerView));
        const containerWidth = this.container.clientWidth;
        const diffPercentage = (diff / containerWidth) * 100;
        
        this.wrapper.style.transform = `translateX(${currentOffset + (diffPercentage / this.currentSlidesPerView)}%)`;
    }

    touchEnd() {
        if (!this.isDragging) return;
        this.isDragging = false;
        
        const diff = this.currentX - this.startX;
        const containerWidth = this.container.clientWidth;
        const threshold = Math.min(containerWidth * 0.15, 40);
        
        if (Math.abs(diff) > threshold) {
            if (diff > 0) {
                this.prev();
            } else {
                this.next();
            }
        } else {
            this.updatePosition();
        }
    }

    getPositionX(event) {
        return event.type.includes('mouse') ? event.pageX : event.touches[0].clientX;
    }

    updateBreakpoints() {
        const width = window.innerWidth;
        let matchedBreakpoint = 0;
        
        for (const bp in this.options.breakpoints) {
            if (width >= parseInt(bp) && parseInt(bp) >= matchedBreakpoint) {
                matchedBreakpoint = parseInt(bp);
            }
        }
        
        const oldSpv = this.currentSlidesPerView;
        
        if (matchedBreakpoint > 0) {
            const bpOptions = this.options.breakpoints[matchedBreakpoint];
            this.currentSlidesPerView = typeof bpOptions.slidesPerView === 'function' ? bpOptions.slidesPerView() : bpOptions.slidesPerView || 1;
        } else {
            this.currentSlidesPerView = this.options.slidesPerView || 1;
        }

        if (this.options.loop && oldSpv !== this.currentSlidesPerView) {
            // Need to re-setup loop because number of clones changes
            this.loopInitialized = false;
            this.currentIndex = this.options.initialSlide; 
        }

        if (this.options.loop) {
            this.setupLoop();
        }
        
        this.updateSlides();
        this.checkDisabled();
        
        if (!this.options.loop) {
            const maxIndex = Math.max(0, this.slides.length - this.currentSlidesPerView);
            if (this.currentIndex > maxIndex) {
                this.currentIndex = maxIndex;
            }
        }
    }

    updateSlides() {
        const slideWidth = 100 / this.currentSlidesPerView;
        this.slides.forEach(slide => {
            slide.style.flex = `0 0 ${slideWidth}%`;
            slide.style.width = `${slideWidth}%`;
            
            slide.querySelectorAll('img').forEach(img => {
                img.ondragstart = () => false;
            });
            slide.querySelectorAll('a').forEach(a => {
                a.ondragstart = () => false;
            });
        });
    }

    updatePosition(animate = true) {
        if (animate) {
            this.wrapper.style.transition = 'transform 0.3s ease-in-out';
            this.isTransitioning = true;
        } else {
            this.wrapper.style.transition = 'none';
            this.isTransitioning = false;
        }
        
        const offset = -(this.currentIndex * (100 / this.currentSlidesPerView));
        
        // Force reflow
        // eslint-disable-next-line no-unused-expressions
        this.wrapper.offsetHeight; 
        
        this.wrapper.style.transform = `translateX(${offset}%)`;
    }

    next() {
        if (this.checkDisabled()) return;
        const maxIndex = Math.max(0, this.slides.length - this.currentSlidesPerView);
        if (this.currentIndex < maxIndex) {
            this.currentIndex++;
        } else if (this.options.loop) {
            this.currentIndex++; // let it transition to clone
        } else if (this.options.rewind) {
            this.currentIndex = 0;
        }
        this.updatePosition();
    }

    prev() {
        if (this.checkDisabled()) return;
        if (this.currentIndex > 0) {
            this.currentIndex--;
        } else if (this.options.loop) {
            this.currentIndex--; // let it transition to clone
        } else if (this.options.rewind) {
            this.currentIndex = Math.max(0, this.slides.length - this.currentSlidesPerView);
        }
        this.updatePosition();
    }

    goTo(originalIndex, animate = false) {
        if (this.checkDisabled()) return;
        
        if (originalIndex < 0 || originalIndex >= this.originalSlides.length) return;

        if (this.options.loop && this.originalSlides.length > this.currentSlidesPerView) {
            this.currentIndex = originalIndex + this.currentSlidesPerView;
        } else {
            this.currentIndex = originalIndex;
        }
        
        this.updatePosition(animate);
    }
}