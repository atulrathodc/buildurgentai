$(document).ready(function(){
	"use strict";
    
        /*==================================
* Author        : "ThemeSine"
* Template Name : Khanas HTML Template
* Version       : 1.0
==================================== */



/*=========== TABLE OF CONTENTS ===========
1. Scroll To Top 
2. Smooth Scroll spy
3. Progress-bar
4. owl carousel
5. welcome animation support
======================================*/

    // 1. Scroll To Top 
		// SCROLL-FRAME COST: the old handler ran jQuery's `.fadeIn()`/`.fadeOut()`
		// on EVERY scroll event. Each of those calls pushes another
		// queued animation and runs the `:visible` filter, which reads
		// offsetWidth/offsetHeight - i.e. a forced synchronous reflow per scroll
		// tick, plus a style write per tick on the fixed "return to top" button.
		// Measured: ~63 forced layout reads per scroll event, first frame ~25ms.
		// Now the handler only flags a frame and the work is coalesced into one
		// rAF tick, touching the DOM only when the visibility state really
		// changed (no per-event animation churn, no per-event reflow).
		var RETURN_TOP_AT = 600;
		var $returnToTop = $('.return-to-top');
		var returnTopShown = false;
		var returnTopTicking = false;

		function syncReturnToTop() {
			returnTopTicking = false;
			var y = window.pageYOffset ||
				(document.documentElement && document.documentElement.scrollTop) ||
				(document.body && document.body.scrollTop) || 0;
			var shouldShow = y > RETURN_TOP_AT;
			if (shouldShow === returnTopShown) { return; }
			returnTopShown = shouldShow;
			if (shouldShow) {
				$returnToTop.stop(true, true).fadeIn();
			} else {
				$returnToTop.stop(true, true).fadeOut();
			}
		}

		$(window).on('scroll', function () {
			if (returnTopTicking) { return; }
			returnTopTicking = true;
			(window.requestAnimationFrame || function (cb) { return window.setTimeout(cb, 16); })(syncReturnToTop);
		});
		syncReturnToTop();
		$('.return-to-top').on('click',function(){
				$('html, body').animate({
				scrollTop: 0
			}, 1500);
			return false;
		});
	
	// 1b. Slideable "Book a Demo" widget (right-edge drawer)
		// The widget (index.html) stays collapsed as a right-edge tab until the
		// user clicks it; the click toggles `.open` so the panel slides in/out.
		$(document).on('click', '.demo-widget-toggle', function () {
			$(this).closest('.demo-widget').toggleClass('open');
			return false;
		});

	// 1c. Slideable "Share" widget (right-edge drawer, same pattern)
		// The share widget (index.html) stays collapsed as a right-edge tab with
		// the social share links; clicking the tab toggles `.open` to slide the
		// panel with the X / Facebook / LinkedIn / WhatsApp links in/out.
		$(document).on('click', '.share-widget-toggle', function () {
			$(this).closest('.share-widget').toggleClass('open');
			return false;
		});

	// 1d. jsSocials (third-party jQuery share plugin) — renders the actual
		// share buttons inside #share-socials. Purely client-side (no account or
		// backend): each network builds its own share URL from the live page URL
		// and opens in a new tab. Must run after jQuery + the jsSocials script
		// (both loaded before custom.js). Wrap in try/catch so a CDN hiccup can
		// never break the rest of the page.
		//
		// LinkedIn is OVERRIDDEN here (not jsSocials' built-in network): jsSocials
		// 1.5.0's built-in handler builds the DEPRECATED
		// `https://www.linkedin.com/shareArticle?mini=true&url=...` endpoint, which
		// LinkedIn no longer honors and opens an EMPTY panel (no title / image / URL
		// preview). The modern endpoint only takes a `url` parameter:
		// `https://www.linkedin.com/sharing/share-offsite/?url=<encodedUrl>`.
		// Because the custom entry keeps `share: 'linkedin'`, jsSocials still emits
		// `.jssocials-share-linkedin`, so the flat-theme styling and the
		// `.share-widget__link--linkedin` color still apply.
		if ($('#share-socials').length) {
			try {
				$('#share-socials').jsSocials({
					showLabel: false,
					showCount: false,
					shares: [
						{ share: 'twitter', label: 'X / Twitter' },
						{ share: 'facebook', label: 'Facebook' },
						{
							share: 'linkedin',
							label: 'LinkedIn',
							logo: 'fa fa-linkedin',
							shareUrl: function () {
								return 'https://www.linkedin.com/sharing/share-offsite/?url=' + encodeURIComponent(window.location.href);
							}
						},
						{ share: 'whatsapp', label: 'WhatsApp' }
					]
				});
			} catch (e) { /* jsSocials unavailable; share buttons simply not rendered */ }
		}
	
	
	
	// 2. Smooth Scroll spy
		
		$('.header-area').sticky({
           topSpacing:0
        });
		
		//=============

		// ONE delegated handler for every `a[href^="#"]` on the page: the header
		// nav, the header "book a demo" CTA, the hero CTAs, the service/showcase
		// tiles and the footer links. The old handler only bound
		// `li.smooth-menu a`, so every other anchor fell through to the browser's
		// own jump - and none of them accounted for the fixed navbar:
		//
		//   * the navbar is `position: fixed` and ~190px tall, so scrolling to a
		//     bare `offset().top` parked the section heading BEHIND it - the
		//     "does not scroll to the right content" symptom;
		//   * the offset is therefore read LIVE from the navbar (+ gap) instead of
		//     hard-coded, so it stays correct at every breakpoint. It matches the
		//     `scroll-margin-top: var(--nav-h)` fallback in style.css, which
		//     covers the browser's own hash navigation (deep links, JS off);
		//   * both roots are animated: whichever of html/body is the scroll
		//     container for the current layout is in the set (see the body rule
		//     in style.css).
		var NAV_GAP = 16; // breathing room between the navbar and the heading

		function navOffset() {
			var $nav = $('nav.navbar.bootsnav');
			return ($nav.length ? $nav.outerHeight() : 0) + NAV_GAP;
		}

		// Sections above the target can still change height around the scroll (the
		// integrations carousel and the showcase rows build themselves as they enter
		// the view, images/fonts settle), which leaves the heading hundreds of px off.
		// Re-check on a short bounded schedule and re-snap whenever it drifted - and
		// do the same after a deep link, where the BROWSER jumps while the page is
		// still short. `attempts` bounds the retries so this can never loop forever.
		//
		// SCROLL JERK: the scheduled re-check used to be unconditional, so the chain
		// kept re-snapping for up to ~1.8s after a click and YANKED the page back to
		// the old heading while the user was already scrolling again - and after two
		// quick nav clicks the abandoned chain of the first one dragged the page
		// away from the second (measured: #capabilities then #contact left the
		// contact section 4800px below the viewport, i.e. the page snapped back).
		// `navToken` is bumped by a new navigation and by real scroll INPUT
		// (wheel / touch / key, none of which programmatic scrolling dispatches),
		// so an outdated chain aborts instead of fighting the user.
		var navToken = 0;

		function align(el, duration, attempts, token) {
			if (token !== navToken) { return; }

			var top = Math.max(0, Math.round($(el).offset().top - navOffset())),
				current = Math.round($(window).scrollTop());

			if (Math.abs(current - top) > 4) {
				$('html, body').stop().animate({
					scrollTop: top
				}, duration === undefined ? 250 : duration);
			}

			if (attempts) {
				window.setTimeout(function () {
					align(el, 250, attempts - 1, token);
				}, 300);
			}
		}

		// the user is in control the moment they touch wheel / trackpad / keyboard
		$(window).on('wheel touchstart keydown', function () {
			navToken++;
		});

		$(window).on('load', function () {
			var el;
			if (location.hash.length > 1) {
				el = document.getElementById(decodeURIComponent(location.hash.slice(1)));
				if (el) {
					align(el, 0, 6, navToken); // instant: this corrects the browser's own jump
				}
			}
		});

		$(document).on('click', 'a[href^="#"]', function (event) {
			var href = $(this).attr('href'),
				el,
				top;

			if (!href || href === '#') {
				return; // a bare "#" is not a target: leave the default alone
			}

			// getElementById (not $(href)) - no selector escaping, and a hash that
			// matches nothing is simply left to the browser.
			el = document.getElementById(decodeURIComponent(href.slice(1)));
			if (!el) {
				return;
			}

			event.preventDefault();

			// a new navigation supersedes any re-snap still scheduled by the
			// previous one (see `navToken` in align())
			navToken++;

			top = Math.max(0, Math.round($(el).offset().top - navOffset()));
			$('html, body').stop().animate({
				scrollTop: top
			}, 900, 'easeInOutExpo', function () {
				align(el, 250, 6, navToken);
			});

			// close the mobile menu: the target must actually be visible once it lands
			var $openMenu = $('.navbar-collapse.in');
			if ($openMenu.length && $.fn.collapse) {
				$openMenu.collapse('hide');
			}

			// keep the URL shareable, but with pushState so the browser does not
			// jump again (which would undo the header offset above)
			if (window.history && history.pushState) {
				history.pushState(null, '', href);
			}
		});
		
		$('body').scrollspy({
			target:'.navbar-collapse',
			offset:0
		});

	// 3. Progress-bar
	
		var dataToggleTooTip = $('[data-toggle="tooltip"]');
		var progressBar = $(".progress-bar");
		if (progressBar.length) {
			// SCROLL-FRAME COST: this used to be `progressBar.appear(...)`.
			// assets/js/jquery.appear.js binds ONE `scroll` handler PER ELEMENT
			// (8 progress bars here), and each of them runs `$(el).is(':visible')`
			// + `$(el).offset()` + `$(el).height()` on EVERY scroll event - every
			// one of those calls flushes layout synchronously in the scroll frame.
			// Measured on the live page: the `:visible` filter alone was the
			// biggest single per-event forced-layout source (~10 reads/event for
			// this section alone, plus the offset/height reads around it).
			// IntersectionObserver reports the exact same "element entered the
			// viewport" moment, from the compositor, with no scroll handler and no
			// layout read at all. `.appear()` stays as the fallback for engines
			// without IO, so the reveal behaviour is unchanged either way.
			var revealProgress = function () {
				if (progressBar.data('buaRevealed')) { return; }
				progressBar.data('buaRevealed', true);
				dataToggleTooTip.tooltip({
					trigger: 'manual'
				}).tooltip('show');
				progressBar.each(function () {
					var each_bar_width = $(this).attr('aria-valuenow');
					$(this).width(each_bar_width + '%');
				});
			};
			if (window.IntersectionObserver) {
				var progressObserver = new window.IntersectionObserver(function (entries, observer) {
					for (var i = 0; i < entries.length; i++) {
						if (entries[i].isIntersecting) {
							observer.disconnect();
							revealProgress();
							return;
						}
					}
				}, { threshold: 0.01 });
				progressBar.each(function () {
					progressObserver.observe(this);
				});
			} else {
				progressBar.appear(revealProgress);
			}
		}
	
	// 4. client carousel (now a custom 3D coverflow slider, see the
	//    `clients3D` module at the bottom of this file - the old flat Owl
	//    Carousel init for `#client` was removed with the broken markup).
		if (window.clients3D && typeof window.clients3D.init === 'function') {
			window.clients3D.init();
		}


    // 5. welcome animation support

        $(window).load(function(){
        	$(".header-text h2,.header-text p").removeClass("animated fadeInUp").css({'opacity':'0'});
            $(".header-text a").removeClass("animated fadeInDown").css({'opacity':'0'});
        });

        $(window).load(function(){
        	$(".header-text h2,.header-text p").addClass("animated fadeInUp").css({'opacity':'0'});
            $(".header-text a").addClass("animated fadeInDown").css({'opacity':'0'});
        });

});


/* ================================================================
   clients3D - dependency-free 3D coverflow slider for the portfolio
   "Clients" section (#client3d). Replaces the old flat Owl Carousel
   strip whose markup had drifted out of sync.

   - true depth: perspective + translateZ/rotateY/scale per ring
   - autoplay that pauses on hover, focus, hidden tab or off-screen
   - drag / swipe, keyboard arrows, generated dots, hover lift
   - responsive card size + visible rings, no horizontal overflow
   - honours prefers-reduced-motion (no autoplay, no transform anim)

   Defensive by design: if the markup (or any part of it) is missing it
   silently no-ops, and it never touches anything outside #client3d.
   Public API: window.clients3D.init() / .refresh()
================================================================ */
(function (window, document) {
    'use strict';

    var ROOT_SELECTOR = '#client3d';
    var AUTOPLAY_MS = 3600;      // dwell time per slide
    var SPACING = 0.62;          // ring spacing as a fraction of the card width
    var DEPTH_STEP = 220;        // px of translateZ per ring (the real depth)
    var MAX_ROTATE = 62;         // deg, hard cap on the coverflow rotation
    var DRAG_FRACTION = 0.42;    // how far you must drag before it flips

    /* [minimum stage width, card width, visible rings] - widest first. */
    var BREAKPOINTS = [
        [1180, 268, 3],
        [900, 240, 3],
        [640, 208, 2],
        [0, 176, 2]
    ];

    function init() {
        var root = document.querySelector(ROOT_SELECTOR);
        if (!root) return null;
        if (root.__clients3d) return root.__clients3d;

        var stage = root.querySelector('.client-3d__stage');
        if (!stage) return null;

        var slides = [].slice.call(stage.querySelectorAll('.client-3d__slide'));
        if (!slides.length) return null;

        var dotsWrap = root.querySelector('[data-client-dots]');
        var prevBtn = root.querySelector('[data-client-prev]');
        var nextBtn = root.querySelector('[data-client-next]');
        var count = slides.length;

        var index = 0;
        var cardW = 0;
        var ring = BREAKPOINTS[BREAKPOINTS.length - 1][2];
        var timer = null;
        var paused = false;
        var inView = true;
        var suppressClick = false;
        var dragX = null;
        var dragUsed = false;
        var rafId = null;
        var lastStageW = -1;   // last stage width we laid the ring out for
        var dots = [];

        var reduce = window.matchMedia
            ? window.matchMedia('(prefers-reduced-motion: reduce)')
            : { matches: false };

        /* ---------- dots (generated, so the markup stays clean) ---------- */
        if (dotsWrap) {
            for (var d = 0; d < count; d++) {
                var dot = document.createElement('button');
                dot.type = 'button';
                dot.className = 'client-3d__dot';
                dot.setAttribute('role', 'tab');
                dot.setAttribute('data-client-dot', String(d));
                dot.setAttribute('aria-label', 'Client ' + (d + 1) + ' of ' + count);
                dotsWrap.appendChild(dot);
                dots.push(dot);
            }
            dotsWrap.addEventListener('click', function (e) {
                var t = e.target && e.target.closest ? e.target.closest('[data-client-dot]') : null;
                if (!t) return;
                goTo(parseInt(t.getAttribute('data-client-dot'), 10), true);
            });
        }

        /* ---------- layout ---------- */
        function measure() {
            var w = stage.clientWidth || root.clientWidth || window.innerWidth || 0;
            var pick = BREAKPOINTS[BREAKPOINTS.length - 1];
            for (var i = 0; i < BREAKPOINTS.length; i++) {
                if (w >= BREAKPOINTS[i][0]) { pick = BREAKPOINTS[i]; break; }
            }
            cardW = pick[1];
            ring = pick[2];
            root.style.setProperty('--c3d-card-w', cardW + 'px');
        }

        /* shortest signed distance from the active slide, with wrap-around */
        function offsetOf(i) {
            var o = i - index;
            var half = count / 2;
            if (o > half) o -= count;
            if (o < -half) o += count;
            return o;
        }

        function apply(animate) {
            root.classList.toggle('is-animating', !!animate && !reduce.matches);
            for (var i = 0; i < count; i++) {
                var slide = slides[i];
                var o = offsetOf(i);
                var a = Math.abs(o);
                var sign = o < 0 ? -1 : (o > 0 ? 1 : 0);
                var x = sign * a * cardW * SPACING;
                var z = -a * DEPTH_STEP;
                var ry = -sign * Math.min(a * 26, MAX_ROTATE);
                var sc = Math.max(0.6, 1 - a * 0.1);
                var visible = a <= ring;

                slide.style.transform =
                    'translate(-50%, -50%)' +
                    ' translateX(' + x.toFixed(1) + 'px)' +
                    ' translateZ(' + z + 'px)' +
                    ' rotateY(' + ry.toFixed(1) + 'deg)' +
                    ' scale(' + sc.toFixed(3) + ')';
                slide.style.opacity = visible
                    ? String(a === 0 ? 1 : Math.max(0.16, 0.84 - (a - 1) * 0.34))
                    : '0';
                slide.style.zIndex = String(100 - a);
                slide.style.pointerEvents = visible ? 'auto' : 'none';

                slide.setAttribute('data-pos', String(a));
                slide.setAttribute('aria-hidden', visible ? 'false' : 'true');

                var link = slide.querySelector('a');
                if (link) link.setAttribute('tabindex', visible ? '0' : '-1');
            }

            for (var k = 0; k < dots.length; k++) {
                var on = k === index;
                dots[k].setAttribute('aria-selected', on ? 'true' : 'false');
                dots[k].setAttribute('tabindex', on ? '0' : '-1');
            }
            root.setAttribute('data-index', String(index));
        }

        /* ---------- navigation ---------- */
        function goTo(i, animate) {
            if (!count) return;
            index = ((i % count) + count) % count;
            apply(animate !== false);
            schedule();
        }

        function go(delta) { goTo(index + delta, true); }

        /* ---------- autoplay: pauses on hover, focus, hidden tab, off-screen */
        function stop() {
            if (timer) { window.clearTimeout(timer); timer = null; }
        }

        function schedule() {
            stop();
            if (reduce.matches || paused || !inView || count < 2) return;
            timer = window.setTimeout(function () {
                timer = null;
                go(1);
            }, AUTOPLAY_MS);
        }

        /* ---------- events ---------- */
        function bind() {
            if (prevBtn) prevBtn.addEventListener('click', function () { go(-1); });
            if (nextBtn) nextBtn.addEventListener('click', function () { go(1); });

            stage.addEventListener('keydown', function (e) {
                var k = e.key;
                if (k === 'ArrowLeft') { e.preventDefault(); go(-1); }
                else if (k === 'ArrowRight') { e.preventDefault(); go(1); }
                else if (k === 'Home') { e.preventDefault(); goTo(0, true); }
                else if (k === 'End') { e.preventDefault(); goTo(count - 1, true); }
            });

            stage.addEventListener('focusin', function (e) {
                paused = true;
                stop();
                var s = e.target && e.target.closest ? e.target.closest('.client-3d__slide') : null;
                if (!s) return;
                var i = slides.indexOf(s);
                if (i >= 0 && i !== index) goTo(i, true);
            });
            stage.addEventListener('focusout', function () {
                paused = false;
                schedule();
            });

            root.addEventListener('mouseenter', function () { paused = true; stop(); });
            root.addEventListener('mouseleave', function () { paused = false; schedule(); });

            /* pointer / touch drag */
            stage.addEventListener('pointerdown', function (e) {
                if (e.pointerType === 'mouse' && e.button !== 0) return;
                dragX = e.clientX;
                dragUsed = false;
                root.classList.add('is-dragging');
            });
            stage.addEventListener('pointermove', function (e) {
                if (dragX === null || dragUsed) return;
                var dx = e.clientX - dragX;
                if (Math.abs(dx) > Math.max(28, cardW * DRAG_FRACTION)) {
                    dragUsed = true;
                    suppressClick = true;
                    go(dx < 0 ? 1 : -1);
                }
            });
            function endDrag() {
                dragX = null;
                root.classList.remove('is-dragging');
            }
            stage.addEventListener('pointerup', endDrag);
            stage.addEventListener('pointercancel', endDrag);
            stage.addEventListener('pointerleave', endDrag);
            stage.addEventListener('dragstart', function (e) { e.preventDefault(); });
            /* swallow the click that ends a real drag so links do not fire */
            stage.addEventListener('click', function (e) {
                if (!suppressClick) return;
                suppressClick = false;
                e.preventDefault();
                e.stopPropagation();
            }, true);

            document.addEventListener('visibilitychange', function () {
                if (document.hidden) { stop(); } else { schedule(); }
            });

            if ('IntersectionObserver' in window) {
                var io = new window.IntersectionObserver(function (entries) {
                    var entry = entries[0];
                    inView = !!(entry && entry.isIntersecting);
                    if (inView) { schedule(); } else { stop(); }
                }, { threshold: 0.15 });
                io.observe(root);
            }

            function relayout() {
                if (rafId) return;
                rafId = window.requestAnimationFrame(function () {
                    rafId = null;
                    var stageW = stage.clientWidth;
                    var before = cardW;
                    measure();
                    /* hover / focus must never re-layout the ring: a ResizeObserver
                       also fires for paint-only churn, so only touch the layout when
                       the stage really changed size (or the card width changed). */
                    if (stageW === lastStageW && cardW === before) return;
                    lastStageW = stageW;
                    if (cardW !== before) apply(false);
                });
            }
            window.addEventListener('resize', relayout);
            window.addEventListener('orientationchange', relayout);
            if ('ResizeObserver' in window) {
                new window.ResizeObserver(relayout).observe(stage);
            }

            if (reduce.addEventListener) {
                reduce.addEventListener('change', function () {
                    paused = false;
                    schedule();
                });
            }
        }

        /* ---------- mount ---------- */
        measure();
        root.classList.add('is-ready');
        bind();
        apply(false);
        schedule();

        var api = {
            go: go,
            goTo: goTo,
            refresh: function () { measure(); apply(false); return api; },
            stop: stop
        };
        root.__clients3d = api;
        return api;
    }

    window.clients3D = {
        init: init,
        refresh: function () {
            var api = init();
            return api ? api.refresh() : null;
        }
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
}(window, document));
	
	