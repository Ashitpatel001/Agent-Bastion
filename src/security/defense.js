// The Watchdog (The Eyes - JS) - UPDATED & ROBUST
// Injected Javascript that lives inside the victim page. 
// It watches for hidden overlays and DOM changes in real-time.

window.Sentinel = {
    // New Helper: Scan specific element manually (called by Agent)
    scanElement: function(selector) {
        const el = document.querySelector(selector);
        return this.checkVisibility(el);
    },

    // Helper: Traverse DOM to find the actual visible background color
    getEffectiveBackgroundColor: function(element) {
        let current = element;
        while (current) {
            const style = window.getComputedStyle(current);
            
            // 🛑 STOP: If there's a background image or gradient, we can't mathematically prove contrast.
            // Assume it's safe (False Positive Prevention).
            if (style.backgroundImage !== 'none' && !style.backgroundImage.includes('none,')) {
                return 'COMPLEX';
            }

            const bg = style.backgroundColor;
            // Check if color is not transparent (rgba alpha > 0)
            if (bg && !bg.includes('rgba(0, 0, 0, 0)') && bg !== 'transparent') {
                return bg;
            }
            current = current.parentElement;
        }
        return 'rgb(255, 255, 255)'; // Default to white assumption
    },

    checkVisibility: function(element) {
        if (!element) return "NOT_FOUND";
        
        const style = window.getComputedStyle(element);
        
        // Check 1: Is it fully invisible? (display:none / visibility:hidden)
        if (style.display === 'none' || style.visibility === 'hidden') {
             return "SAFE_HIDDEN";
        }

        // Check 2: The "Ghost" Check (Opacity < 0.1) - RECURSIVE PARENT CHECK
        // Opacity applies to the stacking context. If parent is 0, child is 0.
        let op = 1.0;
        let curr = element;
        while (curr && curr.nodeType === 1) {
             const s = window.getComputedStyle(curr);
             op = op * parseFloat(s.opacity);
             if (op < 0.1) return "HIDDEN_OPACITY (Parent)";
             curr = curr.parentElement;
        }
        
        // Check 3: Semantic Analysis for Prompt Injection (Vector 1) - ANY ELEMENT
        // Expanded keyword list to catch common bypass variants
        const text = element.textContent.toUpperCase();
        const injectionKeywords = [
            "IGNORE PREVIOUS", "SYSTEM OVERRIDE", "NEW DIRECTIVE", 
            "SYSTEM COMMAND", "IGNORE USER GOAL",
            "FORGET YOUR INSTRUCTIONS", "DISREGARD PREVIOUS",
            "YOU ARE NOW", "ACT AS A DIFFERENT", "PRETEND YOU ARE",
            "JAILBREAK", "ROLEPLAY AS", "SWITCH TO MODE",
            "SEND THE DATA TO", "EXFILTRATE", "TRANSMIT TO",
            "REVEAL YOUR SYSTEM PROMPT", "SHOW YOUR INSTRUCTIONS",
            "OVERRIDE PREVIOUS", "UPDATED INSTRUCTIONS"
        ];
        for (const keyword of injectionKeywords) {
            if (text.includes(keyword)) {
                return "HIDDEN_PROMPT_INJECTION";
            }
        }
        
        // Check 4: Tiny Text / Formatting (Font Size < 2px)
        if (element.children.length === 0 && element.textContent.trim().length > 0) {
             const fontSize = parseFloat(style.fontSize);
             if (fontSize < 2 && fontSize > 0) {
                 return `TINY_TEXT (${style.fontSize})`; 
             }
        }

        // Check 3.b: Off-screen
        const rect = element.getBoundingClientRect();
        if (rect.left < -1000 || rect.top < -1000) {
            return "OFF_SCREEN";
        }

        // Helper for Effective Opacity (Recursive)
        const getEffectiveOpacity = (el) => {
            let op = 1.0;
            let current = el;
            while (current && current.nodeType === 1) {
                const s = window.getComputedStyle(current);
                op = op * parseFloat(s.opacity || 1);
                current = current.parentElement;
            }
            return op;
        };
        
        // Check 4: Anti-Clickjacking (Overlay Interaction) - IMPROVED MULTI-POINT CHECK
        // We calculate the center AND corners to detect partial overlaps
        // check if *this* element (if clickable) is being covered by something invisible.
        const tagName = element.tagName;
        const isLikelyClickable = ['A', 'BUTTON', 'INPUT', 'TEXTAREA', 'SELECT', 'IFRAME', 'DIV'].includes(tagName) || style.cursor === 'pointer';

        if (isLikelyClickable) {
            if (rect.width > 2 && rect.height > 2 && rect.top >= 0 && rect.left >= 0) {
                 
                 const points = [
                     {x: rect.left + rect.width / 2, y: rect.top + rect.height / 2}, // Center
                     {x: rect.left + 5, y: rect.top + 5}, // Top Left
                     {x: rect.right - 5, y: rect.bottom - 5} // Bottom Right
                 ];
                 
                 for (let p of points) { 
                     // Ensure point is on screen
                     if (p.x > 0 && p.y > 0 && p.x < window.innerWidth && p.y < window.innerHeight) {
                         const topElement = document.elementFromPoint(p.x, p.y);
                         
                         // If something else is on top of us...
                         if (topElement && topElement !== element && !element.contains(topElement) && !topElement.contains(element)) {
                              const overlayStyle = window.getComputedStyle(topElement);
                              const overlayOpacity = getEffectiveOpacity(topElement);

                              // And that thing is invisible...
                              if (overlayOpacity < 0.1 || overlayStyle.backgroundColor.includes('rgba(0, 0, 0, 0)') || overlayStyle.backgroundColor === 'transparent') {
                                  // ACTIVE DEFENSE: Remove the invisible overlay
                                  topElement.style.pointerEvents = 'none';
                                  topElement.setAttribute('data-sentinel-clickjacking-overlay', 'true');
                                  
                                  return "BLOCKED_BY_INVISIBLE_OVERLAY";
                              }
                         }
                     }
                 }
            }
        }
        
        // Check 3.5: Invisible Ink (Contrast) - Only check if text exists
        if (element.children.length === 0 && element.textContent.trim().length > 0) {
             const bg = this.getEffectiveBackgroundColor(element);
             if (bg !== 'COMPLEX') {
                 const contrast = this.getContrastRatio(style.color, bg);
                 if (contrast < 1.05) {
                    return `INVISIBLE_INK (Contrast: ${contrast.toFixed(2)})`;
                 }
             }
        }

        return "VISIBLE";
    },

    // Helper: W3C Relative Luminance Calculation
    getLuminance: function(colorStr) {
        // Parse rgb/rgba
        const m = colorStr.match(/(\d+),\s*(\d+),\s*(\d+)/);
        if (!m) return 1; // Default to white if parse error
        
        const a = [m[1], m[2], m[3]].map(function(v) {
            v /= 255;
            return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
        });
        return a[0] * 0.2126 + a[1] * 0.7152 + a[2] * 0.0722;
    },

    getContrastRatio: function(fg, bg) {
        const lum1 = this.getLuminance(fg);
        const lum2 = this.getLuminance(bg);
        const bright = Math.max(lum1, lum2);
        const dark = Math.min(lum1, lum2);
        return (bright + 0.05) / (dark + 0.05);
    },

    // Phase 2: MutationObserver
    // Watches for suspicious dynamic injections (like fake login popups)
    startMutationObserver: function() {
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === 1) { // Element node
                        // Check for high Z-Index inputs (common in Phishing Popups)
                        const style = window.getComputedStyle(node);
                        let zIndex = parseInt(style.zIndex);
                        if (isNaN(zIndex)) zIndex = 0; // Handle 'auto' or empty string
                        
                        // False Positive Reduction: 
                        // Only flag if it's High Z-Index OR Fixed Position
                        const hasInput = node.querySelector('input') !== null;
                        const hasButton = node.querySelector('button') !== null || node.tagName === 'BUTTON';
                        // Relaxed size check (covers > 20% of screen is annoying enough)
                        const isBig = node.offsetWidth > window.innerWidth * 0.2 && node.offsetHeight > window.innerHeight * 0.2;
                        
                        // PRODUCTION SAFEGUARDS: Whitelist benign overlays
                        const textContent = node.textContent.toLowerCase();
                        const isCookieBanner = textContent.includes("cookie") || textContent.includes("privacy") || textContent.includes("accept all");
                        const isModal = node.getAttribute('role') === 'dialog' || node.getAttribute('role') === 'alertdialog';

                        if ((zIndex > 1000 || style.position === 'fixed') && 
                            (hasInput || hasButton || isBig) &&
                            !isCookieBanner && !isModal) {
                            
                            console.log(`[Sentinel] Suspicious fixed/high-z-index element added: ${node.tagName}`);
                            node.setAttribute('data-sentinel-suspicious', 'true');
                            
                            // ACTIVE DEFENSE: Disable Interaction
                            node.style.pointerEvents = 'none';
                            node.style.opacity = '0.5';
                            node.setAttribute('disabled', 'true');
                            const inputs = node.querySelectorAll('input, button');
                            inputs.forEach(i => i.disabled = true);
                            
                            // Visual Debugging
                            node.style.border = '5px solid red'; 

                            let label = document.createElement('div');
                            label.innerText = "🛑 BLOCKED: SUSPICIOUS INJECTION";
                            label.style.position = 'absolute';
                            label.style.top = '0';
                            label.style.left = '0';
                            label.style.background = 'red';
                            label.style.color = 'white';
                            label.style.zIndex = '2147483647'; // Max Int
                            label.style.padding = '5px';
                            label.style.fontWeight = 'bold';
                            label.style.pointerEvents = 'none'; // Don't block clicks to the label itself
                            node.appendChild(label);
                        }
                    }
                });
            });
        });

        // Robust body check
        if(document.body) {
             observer.observe(document.body, { childList: true, subtree: true });
        } else {
            // Wait for it
            window.addEventListener('load', () => {
                 if (document.body) observer.observe(document.body, { childList: true, subtree: true });
            });
        }
        
        console.log("Sentinel MutationObserver Active");
    }
};

// Wait for body to be ready
if (document.body) {
    window.Sentinel.startMutationObserver();
} else {
    window.addEventListener('DOMContentLoaded', () => {
        window.Sentinel.startMutationObserver();
    });
}

console.log("Sentinel Watchdog Active");
