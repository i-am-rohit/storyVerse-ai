/**
 * StoryVerse AI — Landing Page Scripts
 * GSAP animations · AOS scroll reveals · Particle system · Smooth interactions
 */

(function () {
    "use strict";

    /* ------------------------------------------------------------------
       AOS — Animate On Scroll
       ------------------------------------------------------------------ */
    AOS.init({
        duration: 800,
        easing: "ease-out-cubic",
        once: true,
        offset: 60,
        disable: "mobile",
    });

    /* ------------------------------------------------------------------
       GSAP — Hero Entrance Animations
       ------------------------------------------------------------------ */
    gsap.registerPlugin(ScrollTrigger);

    const heroTimeline = gsap.timeline({ defaults: { ease: "power3.out" } });

    heroTimeline
        .from("[data-hero-animate]", {
            y: 40,
            opacity: 0,
            duration: 0.8,
            stagger: 0.15,
        })
        .from(".hero-visual", {
            scale: 0.85,
            opacity: 0,
            duration: 1,
        }, "-=0.4")
        .from(".book-glow", {
            scale: 0,
            opacity: 0,
            duration: 1.2,
        }, "-=0.8");

    /* Hero orbs parallax on scroll */
    gsap.to(".hero-orb--1", {
        y: -80,
        scrollTrigger: {
            trigger: "#hero",
            start: "top top",
            end: "bottom top",
            scrub: 1,
        },
    });

    gsap.to(".hero-orb--2", {
        y: -120,
        scrollTrigger: {
            trigger: "#hero",
            start: "top top",
            end: "bottom top",
            scrub: 1.5,
        },
    });

    /* Section title glow on scroll */
    gsap.utils.toArray(".section-title").forEach((title) => {
        gsap.from(title, {
            y: 30,
            opacity: 0,
            duration: 0.8,
            scrollTrigger: {
                trigger: title,
                start: "top 85%",
                toggleActions: "play none none none",
            },
        });
    });

    /* Pipeline nodes stagger */
    gsap.from(".pipeline-node", {
        scale: 0.8,
        opacity: 0,
        duration: 0.5,
        stagger: 0.1,
        scrollTrigger: {
            trigger: ".cap-visual-body",
            start: "top 80%",
            toggleActions: "play none none none",
        },
    });

    /* CTA card scale-in enhancement */
    gsap.from(".cta-card", {
        y: 50,
        opacity: 0,
        duration: 1,
        scrollTrigger: {
            trigger: ".cta-section",
            start: "top 75%",
            toggleActions: "play none none none",
        },
    });

    /* ------------------------------------------------------------------
       Floating Particle Canvas
       ------------------------------------------------------------------ */
    const canvas = document.getElementById("particle-canvas");
    if (canvas) {
        const ctx = canvas.getContext("2d");
        let particles = [];
        let animationId;
        let mouse = { x: null, y: null, radius: 120 };

        function resizeCanvas() {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        }

        class Particle {
            constructor() {
                this.reset();
            }

            reset() {
                this.x = Math.random() * canvas.width;
                this.y = Math.random() * canvas.height;
                this.size = Math.random() * 2 + 0.5;
                this.speedX = (Math.random() - 0.5) * 0.4;
                this.speedY = (Math.random() - 0.5) * 0.4;
                this.opacity = Math.random() * 0.5 + 0.1;
                const colors = ["#3b82f6", "#8b5cf6", "#00d4ff", "#a855f7"];
                this.color = colors[Math.floor(Math.random() * colors.length)];
            }

            update() {
                this.x += this.speedX;
                this.y += this.speedY;

                if (mouse.x !== null) {
                    const dx = this.x - mouse.x;
                    const dy = this.y - mouse.y;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    if (dist < mouse.radius) {
                        const force = (mouse.radius - dist) / mouse.radius;
                        this.x += (dx / dist) * force * 2;
                        this.y += (dy / dist) * force * 2;
                    }
                }

                if (this.x < 0 || this.x > canvas.width) this.speedX *= -1;
                if (this.y < 0 || this.y > canvas.height) this.speedY *= -1;
            }

            draw() {
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
                ctx.fillStyle = this.color;
                ctx.globalAlpha = this.opacity;
                ctx.fill();
                ctx.globalAlpha = 1;
            }
        }

        function initParticles() {
            const count = Math.min(Math.floor(window.innerWidth / 12), 100);
            particles = [];
            for (let i = 0; i < count; i++) {
                particles.push(new Particle());
            }
        }

        function connectParticles() {
            for (let i = 0; i < particles.length; i++) {
                for (let j = i + 1; j < particles.length; j++) {
                    const dx = particles[i].x - particles[j].x;
                    const dy = particles[i].y - particles[j].y;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    if (dist < 120) {
                        ctx.beginPath();
                        ctx.strokeStyle = `rgba(59, 130, 246, ${0.08 * (1 - dist / 120)})`;
                        ctx.lineWidth = 0.5;
                        ctx.moveTo(particles[i].x, particles[i].y);
                        ctx.lineTo(particles[j].x, particles[j].y);
                        ctx.stroke();
                    }
                }
            }
        }

        function animateParticles() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            particles.forEach((p) => {
                p.update();
                p.draw();
            });
            connectParticles();
            animationId = requestAnimationFrame(animateParticles);
        }

        resizeCanvas();
        initParticles();
        animateParticles();

        window.addEventListener("resize", () => {
            resizeCanvas();
            initParticles();
        });

        window.addEventListener("mousemove", (e) => {
            mouse.x = e.clientX;
            mouse.y = e.clientY;
        });

        window.addEventListener("mouseleave", () => {
            mouse.x = null;
            mouse.y = null;
        });
    }

    /* ------------------------------------------------------------------
       Navbar — Scroll Effect & Mobile Toggle
       ------------------------------------------------------------------ */
    const nav = document.getElementById("landing-nav");
    const navToggle = document.getElementById("nav-toggle");
    const navLinks = document.getElementById("nav-links");

    if (nav) {
        window.addEventListener("scroll", () => {
            nav.classList.toggle("scrolled", window.scrollY > 40);
        });
    }

    if (navToggle && navLinks) {
        navToggle.addEventListener("click", () => {
            const isOpen = navLinks.classList.toggle("open");
            navToggle.classList.toggle("active", isOpen);
            navToggle.setAttribute("aria-expanded", isOpen);
            document.body.style.overflow = isOpen ? "hidden" : "";
        });

        navLinks.querySelectorAll(".nav-link").forEach((link) => {
            link.addEventListener("click", () => {
                navLinks.classList.remove("open");
                navToggle.classList.remove("active");
                navToggle.setAttribute("aria-expanded", "false");
                document.body.style.overflow = "";
            });
        });
    }

    /* ------------------------------------------------------------------
       Smooth Scroll for Anchor Links
       ------------------------------------------------------------------ */
    document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
        anchor.addEventListener("click", (e) => {
            const targetId = anchor.getAttribute("href");
            if (targetId === "#") return;

            const target = document.querySelector(targetId);
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: "smooth" });
            }
        });
    });

    /* ------------------------------------------------------------------
       Hover Glow — Mouse-tracking glow on cards
       ------------------------------------------------------------------ */
    document.querySelectorAll(".feature-card, .testimonial, .agent-item").forEach((card) => {
        card.addEventListener("mousemove", (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            card.style.background = `
                radial-gradient(
                    400px circle at ${x}px ${y}px,
                    rgba(59, 130, 246, 0.08),
                    rgba(255, 255, 255, 0.04) 40%
                )
            `;
        });

        card.addEventListener("mouseleave", () => {
            card.style.background = "";
        });
    });

    /* ------------------------------------------------------------------
       Magnetic Button Effect (subtle)
       ------------------------------------------------------------------ */
    document.querySelectorAll(".btn-primary, .btn-glass").forEach((btn) => {
        btn.addEventListener("mousemove", (e) => {
            const rect = btn.getBoundingClientRect();
            const x = e.clientX - rect.left - rect.width / 2;
            const y = e.clientY - rect.top - rect.height / 2;
            btn.style.transform = `translate(${x * 0.08}px, ${y * 0.08}px)`;
        });

        btn.addEventListener("mouseleave", () => {
            btn.style.transform = "";
        });
    });

})();
