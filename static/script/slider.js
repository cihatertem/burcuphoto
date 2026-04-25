class VanillaSlider {
    constructor(selector, options = {}) {
        this.container = typeof selector === 'string' ? document.querySelector(selector) : selector;
        if (!this.container) return;

        this.wrapper = this.container.querySelector('.slider-wrapper');
        this.slides = Array.from(this.wrapper.children);
        this.nextBtn = this.container.querySelector('.slider-button-next');
        this.prevBtn = this.container.querySelector('.slider-button-prev');
        
        this.options = Object.assign({
            rewind: false,
            initialSlide: 0,
            slidesPerView: 1,
            breakpoints: {}
        }, options);

        this.currentIndex = this.options.initialSlide;
        this.currentSlidesPerView = this.options.slidesPerView;

        // Swipe & drag variables
        this.startX = 0;
        this.currentX = 0;
        this.isDragging = false;
        this.moved = false;

        this.init();
    }

    init() {
        this.updateBreakpoints();
        window.addEventListener('resize', () => {
            this.updateBreakpoints();
            this.updatePosition();
        });

        if (this.nextBtn) {
            this.nextBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.next();
            });
        }
        if (this.prevBtn) {
            this.prevBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.prev();
            });
        }
        
        // Touch events for mobile
        this.wrapper.addEventListener('touchstart', this.touchStart.bind(this), {passive: true});
        this.wrapper.addEventListener('touchmove', this.touchMove.bind(this), {passive: true});
        this.wrapper.addEventListener('touchend', this.touchEnd.bind(this));
        
        // Mouse events for desktop dragging
        this.wrapper.addEventListener('mousedown', this.touchStart.bind(this));
        this.wrapper.addEventListener('mousemove', this.touchMove.bind(this));
        this.wrapper.addEventListener('mouseup', this.touchEnd.bind(this));
        this.wrapper.addEventListener('mouseleave', this.touchEnd.bind(this));

        // Prevent clicking if we dragged
        this.wrapper.addEventListener('click', (e) => {
            if (this.moved) {
                e.preventDefault();
                e.stopPropagation();
                this.moved = false;
            }
        }, { capture: true });

        this.updateSlides();
        this.updatePosition();
    }

    touchStart(event) {
        this.isDragging = true;
        this.moved = false;
        this.startX = this.getPositionX(event);
        this.currentX = this.startX;
        this.wrapper.style.transition = 'none'; // Remove transition for 1:1 finger tracking
    }

    touchMove(event) {
        if (!this.isDragging) return;
        this.currentX = this.getPositionX(event);
        const diff = this.currentX - this.startX;
        
        // Track if we moved enough to consider it a swipe/drag (ignore tiny accidental movements)
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
        
        // Swipe threshold: 15% of container width or at least 40px
        const threshold = Math.min(containerWidth * 0.15, 40);
        
        if (Math.abs(diff) > threshold) {
            if (diff > 0) {
                this.prev();
            } else {
                this.next();
            }
        } else {
            // Revert back if not dragged enough
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
        
        if (matchedBreakpoint > 0) {
            const bpOptions = this.options.breakpoints[matchedBreakpoint];
            const spv = typeof bpOptions.slidesPerView === 'function' ? bpOptions.slidesPerView() : bpOptions.slidesPerView;
            this.currentSlidesPerView = spv || 1;
        } else {
            this.currentSlidesPerView = this.options.slidesPerView || 1;
        }

        this.updateSlides();
        
        const maxIndex = Math.max(0, this.slides.length - this.currentSlidesPerView);
        if (this.currentIndex > maxIndex) {
            this.currentIndex = maxIndex;
            this.updatePosition();
        }
    }

    updateSlides() {
        const slideWidth = 100 / this.currentSlidesPerView;
        this.slides.forEach(slide => {
            slide.style.flex = `0 0 ${slideWidth}%`;
            slide.style.width = `${slideWidth}%`;
            
            // Prevent default image drag to not interfere with mouse swiping
            slide.querySelectorAll('img').forEach(img => {
                img.ondragstart = () => false;
            });
            // Also prevent dragging on anchor tags
            slide.querySelectorAll('a').forEach(a => {
                a.ondragstart = () => false;
            });
        });
    }

    updatePosition() {
        this.wrapper.style.transition = 'transform 0.3s ease-in-out';
        const maxIndex = Math.max(0, this.slides.length - this.currentSlidesPerView);
        if (this.currentIndex > maxIndex) {
            this.currentIndex = maxIndex;
        }
        const offset = -(this.currentIndex * (100 / this.currentSlidesPerView));
        this.wrapper.style.transform = `translateX(${offset}%)`;
    }

    next() {
        const maxIndex = Math.max(0, this.slides.length - this.currentSlidesPerView);
        if (this.currentIndex < maxIndex) {
            this.currentIndex++;
        } else if (this.options.rewind) {
            this.currentIndex = 0;
        }
        this.updatePosition();
    }

    prev() {
        if (this.currentIndex > 0) {
            this.currentIndex--;
        } else if (this.options.rewind) {
            this.currentIndex = Math.max(0, this.slides.length - this.currentSlidesPerView);
        }
        this.updatePosition();
    }
}