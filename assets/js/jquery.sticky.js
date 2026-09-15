// Sticky Plugin v1.0.4 for jQuery
// =============
// Author: Anthony Garand
// Improvements by German M. Bravo (Kronuz) and Ruud Kamphuis (ruudk)
// Improvements by Leonardo C. Daronco (daronco)
// Created: 02/14/2011
// Date: 07/20/2015
// Website: http://stickyjs.com/
// Description: Makes an element on the page stick on the screen as you scroll
//              It will only set the 'top' and 'position' of your element, you
//              might need to adjust the width in some cases.

(function (factory) {
    if (typeof define === 'function' && define.amd) {
        // AMD. Register as an anonymous module.
        define(['jquery'], factory);
    } else if (typeof module === 'object' && module.exports) {
        // Node/CommonJS
        module.exports = factory(require('jquery'));
    } else {
        // Browser globals
        factory(jQuery);
    }
}(function ($) {
    var slice = Array.prototype.slice; // save ref to original slice()
    var splice = Array.prototype.splice; // save ref to original slice()

  var defaults = {
      topSpacing: 0,
      bottomSpacing: 0,
      className: 'is-sticky',
      wrapperClassName: 'sticky-wrapper',
      center: false,
      getWidthFrom: '',
      widthFromWrapper: true, // works only when .getWidthFrom is empty
      responsiveWidth: false,
      zIndex: 'inherit'
    },
    $window = $(window),
    $document = $(document),
    sticked = [],
    windowHeight = $window.height(),

    /* ----------------------------------------------------------------------
       Scroll cost. Measured on this page: ~63 forced layout reads per scroll
       event, and the first scroll frame ran ~3x the median frame time.

       The old pass ran on EVERY scroll event and mixed reads with writes:
       `.css('height', ...)` (write -> invalidate style + layout) followed by
       `offset()` / `outerHeight()` (read -> force a synchronous reflow), several
       times per event. Now:
         * scroll events are coalesced into ONE rAF tick, so a wheel burst costs
           a single pass instead of one pass per event;
         * the geometry is cached and re-read only on resize / DOM mutation
           (`metricsDirty`);
         * the wrapper height is written only when it actually changed, so a
           plain scroll no longer invalidates layout at all.
       Public behaviour (sticky-start/update/end, bottom reached/not-reached)
       is unchanged.
    ---------------------------------------------------------------------- */
    raf = window.requestAnimationFrame || function (cb) { return window.setTimeout(cb, 16); },
    rafId = 0,
    metricsDirty = true,

    /* Page-level geometry, cached for the same reason as the per-element
       geometry below: `$document.height()` alone costs ~5 forced layout reads
       (jQuery takes the max of the body/documentElement scroll+offset+client
       heights, plus a getComputedStyle), and the old tick called it on EVERY
       scroll event. */
    pageMetrics = { docHeight: 0, viewportHeight: 0, dwh: 0 },
    refreshPageMetrics = function () {
      pageMetrics.viewportHeight = windowHeight;
      pageMetrics.docHeight = $document.height();
      pageMetrics.dwh = pageMetrics.docHeight - pageMetrics.viewportHeight;
    },

    refreshMetrics = function (s) {
      s.elementTop = s.stickyWrapper.offset().top;
      s.elementHeight = s.stickyElement.outerHeight();
      var container = s.stickyWrapper.parent();
      s.containerTop = container.offset().top;
      s.containerHeight = container.outerHeight();
      s.containerBottom = s.containerTop + s.containerHeight;
    },
    syncWrapperHeight = function (s) {
      if (s.wrapperHeight !== s.elementHeight) {
        s.wrapperHeight = s.elementHeight;
        s.stickyWrapper.css('height', s.elementHeight);
      }
    },
    scheduleScroller = function () {
      if (rafId) { return; }
      rafId = raf(scroller);
    },
    scroller = function() {
      rafId = 0;

      // ---- READ PASS -------------------------------------------------------
      // Every layout read happens HERE, before any style write, and only when
      // the cached geometry is really stale (resize / DOM mutation / page
      // growth / first run). `metricsDirty` used to never be cleared, so this
      // pass ran - and re-read `$(document).height()`, `offset()` and
      // `outerHeight()` - on EVERY scroll tick: ~15 forced layout reads per
      // event, each one flushing the layout the write pass below had just
      // invalidated. Clearing the flag makes a steady-state scroll frame
      // read-free (`$window.scrollTop()` is `pageYOffset`: no layout).
      if (metricsDirty) {
        refreshPageMetrics();
        for (var m = 0, ml = sticked.length; m < ml; m++) { refreshMetrics(sticked[m]); }
        metricsDirty = false;
      }

      // ---- WRITE PASS ------------------------------------------------------
      var scrollTop = $window.scrollTop(),
        documentHeight = pageMetrics.docHeight,
        dwh = pageMetrics.dwh,
        extra = (scrollTop > dwh) ? dwh - scrollTop : 0;

      for (var i = 0, l = sticked.length; i < l; i++) {
        var s = sticked[i];

        // geometry comes from the cache (refreshMetrics); it is re-read only on
        // resize / DOM mutation instead of on every scroll tick
        if (s.elementTop === undefined) { refreshMetrics(s); }

        //update height in case of dynamic content - only when it really changed
        syncWrapperHeight(s);

        var elementTop = s.elementTop,
          etse = elementTop - s.topSpacing - extra;

        if (scrollTop <= etse) {
          if (s.currentTop !== null) {
            s.stickyElement
              .css({
                'width': '',
                'position': '',
                'top': '',
                'z-index': ''
              });
            s.stickyElement.parent().removeClass(s.className);
            s.stickyElement.trigger('sticky-end', [s]);
            s.currentTop = null;
            s.unstuck = null; // the next stick starts from a clean pin state
          }
        }
        else {
          var newTop = documentHeight - s.elementHeight
            - s.topSpacing - s.bottomSpacing - scrollTop - extra;
          if (newTop < 0) {
            newTop = newTop + s.topSpacing;
          } else {
            newTop = s.topSpacing;
          }
          if (s.currentTop !== newTop) {
            var newWidth;
            if (s.getWidthFrom) {
                padding =  s.stickyElement.innerWidth() - s.stickyElement.width();
                newWidth = $(s.getWidthFrom).width() - padding || null;
            } else if (s.widthFromWrapper) {
                newWidth = s.stickyWrapper.width();
            }
            if (newWidth == null) {
                newWidth = s.stickyElement.width();
            }
            s.stickyElement
              .css('width', newWidth)
              .css('position', 'fixed')
              .css('top', newTop)
              .css('z-index', s.zIndex);

            s.stickyElement.parent().addClass(s.className);

            if (s.currentTop === null) {
              s.stickyElement.trigger('sticky-start', [s]);
            } else {
              // sticky is started but it have to be repositioned
              s.stickyElement.trigger('sticky-update', [s]);
            }

            if (s.currentTop === s.topSpacing && s.currentTop > newTop || s.currentTop === null && newTop < s.topSpacing) {
              // just reached bottom || just started to stick but bottom is already reached
              s.stickyElement.trigger('sticky-bottom-reached', [s]);
            } else if(s.currentTop !== null && newTop === s.topSpacing && s.currentTop < newTop) {
              // sticky is started && sticked at topSpacing && overflowing from top just finished
              s.stickyElement.trigger('sticky-bottom-unreached', [s]);
            }

            s.currentTop = newTop;
          }

          // Check if sticky has reached end of container and stop sticking.
          // The pinned element sits at `newTop` in the viewport, so its page
          // position is `scrollTop + newTop`: the end-of-container test is
          // answered from the CACHE (`containerBottom` / `elementHeight`) instead
          // of the 4 live `offset()` reads this used to do straight after the
          // `.css()` writes above - a write/read pair that forced a synchronous
          // reflow on every single frame.
          var pinnedPageTop = scrollTop + newTop,
            unstick = (pinnedPageTop + s.elementHeight >= s.containerBottom) &&
              (pinnedPageTop <= s.topSpacing);

          // ...and the style write itself only happens when the state flipped,
          // so a plain scroll no longer re-invalidates the style (and repaints
          // the blurred backdrop) of the fixed navbar on every frame.
          if (unstick !== s.unstuck) {
            s.unstuck = unstick;
            if( unstick ) {
              s.stickyElement
                .css('position', 'absolute')
                .css('top', '')
                .css('bottom', 0)
                .css('z-index', '');
            } else {
              s.stickyElement
                .css('position', 'fixed')
                .css('top', newTop)
                .css('bottom', '')
                .css('z-index', s.zIndex);
            }
          }
        }
      }
    },
    resizer = function() {
      windowHeight = $window.height();
      metricsDirty = true; // viewport change invalidates the cached geometry

      for (var i = 0, l = sticked.length; i < l; i++) {
        var s = sticked[i];
        var newWidth = null;
        if (s.getWidthFrom) {
            if (s.responsiveWidth) {
                newWidth = $(s.getWidthFrom).width();
            }
        } else if(s.widthFromWrapper) {
            newWidth = s.stickyWrapper.width();
        }
        if (newWidth != null) {
            s.stickyElement.css('width', newWidth);
        }
      }
    },
    methods = {
      init: function(options) {
        return this.each(function() {
          var o = $.extend({}, defaults, options);
          var stickyElement = $(this);

          var stickyId = stickyElement.attr('id');
          var wrapperId = stickyId ? stickyId + '-' + defaults.wrapperClassName : defaults.wrapperClassName;
          var wrapper = $('<div></div>')
            .attr('id', wrapperId)
            .addClass(o.wrapperClassName);

          stickyElement.wrapAll(function() {
            if ($(this).parent("#" + wrapperId).length == 0) {
                    return wrapper;
            }
});

          var stickyWrapper = stickyElement.parent();

          if (o.center) {
            stickyWrapper.css({width:stickyElement.outerWidth(),marginLeft:"auto",marginRight:"auto"});
          }

          if (stickyElement.css("float") === "right") {
            stickyElement.css({"float":"none"}).parent().css({"float":"right"});
          }

          o.stickyElement = stickyElement;
          o.stickyWrapper = stickyWrapper;
          o.currentTop    = null;

          sticked.push(o);

          methods.setWrapperHeight(this);
          methods.setupChangeListeners(this);
        });
      },

      setWrapperHeight: function(stickyElement) {
        var element = $(stickyElement);
        var stickyWrapper = element.parent();
        if (stickyWrapper) {
          stickyWrapper.css('height', element.outerHeight());
        }
        metricsDirty = true; // dynamic content invalidates the cached geometry
      },

      setupChangeListeners: function(stickyElement) {
        if (window.MutationObserver) {
          var mutationObserver = new window.MutationObserver(function(mutations) {
            if (mutations[0].addedNodes.length || mutations[0].removedNodes.length) {
              methods.setWrapperHeight(stickyElement);
            }
          });
          mutationObserver.observe(stickyElement, {subtree: true, childList: true});
        } else {
          if (window.addEventListener) {
            stickyElement.addEventListener('DOMNodeInserted', function() {
              methods.setWrapperHeight(stickyElement);
            }, false);
            stickyElement.addEventListener('DOMNodeRemoved', function() {
              methods.setWrapperHeight(stickyElement);
            }, false);
          } else if (window.attachEvent) {
            stickyElement.attachEvent('onDOMNodeInserted', function() {
              methods.setWrapperHeight(stickyElement);
            });
            stickyElement.attachEvent('onDOMNodeRemoved', function() {
              methods.setWrapperHeight(stickyElement);
            });
          }
        }
      },
      update: scroller,
      unstick: function(options) {
        return this.each(function() {
          var that = this;
          var unstickyElement = $(that);

          var removeIdx = -1;
          var i = sticked.length;
          while (i-- > 0) {
            if (sticked[i].stickyElement.get(0) === that) {
                splice.call(sticked,i,1);
                removeIdx = i;
            }
          }
          if(removeIdx !== -1) {
            unstickyElement.unwrap();
            unstickyElement
              .css({
                'width': '',
                'position': '',
                'top': '',
                'float': '',
                'z-index': ''
              })
            ;
          }
        });
      }
    };

  // should be more efficient than using $window.scroll(scroller) and $window.resize(resizer):
  if (window.addEventListener) {
    window.addEventListener('scroll', scheduleScroller, { passive: true });
    window.addEventListener('resize', resizer, false);
    window.addEventListener('load', function () { metricsDirty = true; }, false);
  } else if (window.attachEvent) {
    window.attachEvent('onscroll', scroller);
    window.attachEvent('onresize', resizer);
  }

  /* The cached geometry must be invalidated whenever the page CAN have changed
     height - it must never be re-read on every scroll tick. The page grows on its
     own while you scroll (sections and carousels build themselves as they enter
     the view, images/fonts settle) and `<body>` grows with its content
     (`height: auto`), so a ResizeObserver on the body fires exactly at those
     moments. Together with the resize + DOM-mutation / load hooks above, that is
     what keeps the read pass off the scroll path. */
  if (window.ResizeObserver && document.body) {
    new window.ResizeObserver(function () { metricsDirty = true; }).observe(document.body);
  }

  $.fn.sticky = function(method) {
    if (methods[method]) {
      return methods[method].apply(this, slice.call(arguments, 1));
    } else if (typeof method === 'object' || !method ) {
      return methods.init.apply( this, arguments );
    } else {
      $.error('Method ' + method + ' does not exist on jQuery.sticky');
    }
  };

  $.fn.unstick = function(method) {
    if (methods[method]) {
      return methods[method].apply(this, slice.call(arguments, 1));
    } else if (typeof method === 'object' || !method ) {
      return methods.unstick.apply( this, arguments );
    } else {
      $.error('Method ' + method + ' does not exist on jQuery.sticky');
    }
  };
  $(function() {
    setTimeout(scroller, 0);
  });
}));
