// Custom JavaScript for enhanced UI/UX with micro-interactions

document.addEventListener('DOMContentLoaded', function() {
    // Debug: confirm this updated script is loaded in the browser
    try { console.log('[debug] custom.js (v2) loaded. Chatbot endpoint: /api/chatbot/'); } catch(e) {}
    // Progress bar loader for page loads
    const progressBar = document.createElement('div');
    progressBar.className = 'progress-bar-loader';
    document.body.appendChild(progressBar);

    // Hide progress bar when page loads
    window.addEventListener('load', function() {
        setTimeout(() => {
            progressBar.style.display = 'none';
        }, 500);
    });

    // Loading spinner for recommendations
    const recommendationLoader = document.createElement('div');
    recommendationLoader.className = 'recommendation-loader';
    recommendationLoader.innerHTML = '<div class="spinner-border-ai" role="status"><span class="visually-hidden">Loading...</span></div>';
    document.body.appendChild(recommendationLoader);

    // Enhanced chatbot with slide-up animation
    const chatbotToggle = document.getElementById('chatbot-toggle');
    const chatbot = document.getElementById('chatbot');
    const chatbotClose = document.getElementById('chatbot-close');
    const chatInput = document.getElementById('chat-input');
    const chatSend = document.getElementById('chat-send');
    const chatMessages = document.getElementById('chat-messages');
    const imageBtn = document.getElementById('image-btn');
    const imageUpload = document.getElementById('image-upload');

    if (chatbotToggle && chatbot) {
        chatbotToggle.addEventListener('click', () => {
            chatbot.classList.toggle('show');
            if (chatbot.classList.contains('show')) {
                chatInput.focus();
            }
        });

        if (chatbotClose) {
            chatbotClose.addEventListener('click', () => {
                chatbot.classList.remove('show');
            });
        }

        // Image upload button
        if (imageBtn && imageUpload) {
            imageBtn.addEventListener('click', () => {
                imageUpload.click();
            });
        }

        function sendMessage() {
            const query = chatInput.value.trim();
            const imageFile = document.getElementById('image-upload').files[0];

            if (!query && !imageFile) return;

            // Add user message with animation
            const userMessage = document.createElement('div');
            userMessage.className = 'message user';
            userMessage.style.opacity = '0';
            userMessage.style.transform = 'translateY(20px)';

            if (imageFile) {
                userMessage.innerHTML = `<img src="${URL.createObjectURL(imageFile)}" style="max-width: 200px; max-height: 200px; border-radius: 8px; margin-bottom: 8px;"><br>${query || 'Image search'}`;
            } else {
                userMessage.textContent = query;
            }

            chatMessages.appendChild(userMessage);

            // Animate message appearance
            setTimeout(() => {
                userMessage.style.transition = 'all 0.3s ease';
                userMessage.style.opacity = '1';
                userMessage.style.transform = 'translateY(0)';
            }, 10);

            chatInput.value = '';
            document.getElementById('image-upload').value = '';
            chatMessages.scrollTop = chatMessages.scrollHeight;

            // Show typing indicator with animation
            const typingIndicator = document.createElement('div');
            typingIndicator.className = 'message bot';
            typingIndicator.style.opacity = '0';
            typingIndicator.style.transform = 'translateY(20px)';
            typingIndicator.innerHTML = '<em>AI is thinking...</em>';
            chatMessages.appendChild(typingIndicator);

            setTimeout(() => {
                typingIndicator.style.transition = 'all 0.3s ease';
                typingIndicator.style.opacity = '1';
                typingIndicator.style.transform = 'translateY(0)';
            }, 10);

            // Simulate AI processing with loader
            recommendationLoader.classList.add('show');

            // Prepare request data
            let requestData;
            let headers = { 'X-CSRFToken': getCSRFToken() };

            if (imageFile) {
                // Send image for visual search
                requestData = new FormData();
                requestData.append('image', imageFile);
                if (query) requestData.append('query', query);
            } else {
                // Send text query
                requestData = JSON.stringify({ query });
                headers['Content-Type'] = 'application/json';
            }

            // Send to API with timeout and robust handling
            const controller = new AbortController();
            const signal = controller.signal;
            const CLIENT_TIMEOUT_MS = 8000; // client-side timeout
            const timeoutId = setTimeout(() => controller.abort(), CLIENT_TIMEOUT_MS);

                        fetch('/api/chatbot/', {
                method: 'POST',
                headers: headers,
                body: requestData,
                signal: signal
            })
            .then(response => {
                clearTimeout(timeoutId);
                recommendationLoader.classList.remove('show');
                // Remove typing indicator if still present
                if (typingIndicator && typingIndicator.parentNode) {
                    try { chatMessages.removeChild(typingIndicator); } catch(e) {}
                }

                if (!response.ok) {
                    return response.text().then(text => {
                        throw new Error(text || 'Server error');
                    });
                }

                // Try to parse JSON, but tolerate non-JSON
                return response.text().then(txt => {
                    try { return JSON.parse(txt); } catch(e) { return { response: txt }; }
                });
            })
            .then(data => {
                const botMessage = document.createElement('div');
                botMessage.className = 'message bot';
                botMessage.style.opacity = '0';
                botMessage.style.transform = 'translateY(20px)';

                let text = '';
                if (!data) {
                    text = 'Sorry, I did not get a response. Please try again.';
                } else if (data.response) {
                    text = data.response;
                } else if (data.results && Array.isArray(data.results)) {
                    // Visual search or structured response
                    if (data.results.length === 0) text = 'No similar books found.';
                    else {
                        text = 'I found similar books: ' + data.results.slice(0,3).map(r => r.title).join(', ');
                    }
                } else if (typeof data === 'string') {
                    text = data;
                } else {
                    text = JSON.stringify(data).slice(0, 500);
                }

                botMessage.textContent = text;
                chatMessages.appendChild(botMessage);

                setTimeout(() => {
                    botMessage.style.transition = 'all 0.3s ease';
                    botMessage.style.opacity = '1';
                    botMessage.style.transform = 'translateY(0)';
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                }, 10);
            })
            .catch(error => {
                clearTimeout(timeoutId);
                recommendationLoader.classList.remove('show');
                if (typingIndicator && typingIndicator.parentNode) {
                    try { chatMessages.removeChild(typingIndicator); } catch(e) {}
                }

                const errorMessage = document.createElement('div');
                errorMessage.className = 'message bot';
                errorMessage.style.opacity = '0';
                errorMessage.style.transform = 'translateY(20px)';

                if (error.name === 'AbortError') {
                    errorMessage.textContent = 'Request timed out. Please try again.';
                } else {
                    errorMessage.textContent = 'Sorry, I encountered an error. Please try again.';
                    console.error('Chatbot request error:', error);
                }

                chatMessages.appendChild(errorMessage);

                setTimeout(() => {
                    errorMessage.style.transition = 'all 0.3s ease';
                    errorMessage.style.opacity = '1';
                    errorMessage.style.transform = 'translateY(0)';
                }, 10);
            });
        }

        if (chatSend) {
            chatSend.addEventListener('click', sendMessage);
        }

        if (chatInput) {
            chatInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') sendMessage();
            });
        }
    }

    // Enhanced wishlist functionality with toast notifications
    document.querySelectorAll('.wishlist-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            this.classList.toggle('active');
            const icon = this.querySelector('i');
            const isActive = this.classList.contains('active');

            // Animate icon
            icon.style.transform = 'scale(0.8)';
            setTimeout(() => {
                icon.style.transform = 'scale(1.2)';
                setTimeout(() => {
                    icon.style.transform = 'scale(1)';
                }, 150);
            }, 50);

            if (isActive) {
                icon.className = 'fas fa-heart';
                showToast('Added to wishlist!', 'success');
            } else {
                icon.className = 'far fa-heart';
                showToast('Removed from wishlist!', 'info');
            }
        });
    });

    // Visual search modal
    const visualSearchBtn = document.querySelector('label[for="visualSearch"]');
    const visualSearchInput = document.getElementById('visualSearch');

    if (visualSearchBtn && visualSearchInput) {
        const modal = createVisualSearchModal();
        document.body.appendChild(modal);

        visualSearchBtn.addEventListener('click', (e) => {
            e.preventDefault();
            modal.classList.add('show');
        });

        // Handle file upload in modal
        const uploadZone = modal.querySelector('.upload-zone');
        const fileInput = modal.querySelector('#modal-visual-search');

        uploadZone.addEventListener('click', () => fileInput.click());

        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.classList.add('dragover');
        });

        uploadZone.addEventListener('dragleave', () => {
            uploadZone.classList.remove('dragover');
        });

        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleFileUpload(files[0]);
            }
        });

        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                handleFileUpload(e.target.files[0]);
            }
        });

        function handleFileUpload(file) {
            if (file && file.type.startsWith('image/')) {
                const formData = new FormData();
                formData.append('image', file);

                // Show loading
                uploadZone.innerHTML = '<div class="spinner-border-ai" role="status"><span class="visually-hidden">Processing...</span></div><p>Analyzing image...</p>';

                fetch('/api/visual-search/', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': getCSRFToken()
                    }
                })
                .then(response => response.json())
                .then(data => {
                    modal.classList.remove('show');
                    if (data.length > 0) {
                        showToast('Found similar books! Redirecting...', 'success');
                        setTimeout(() => {
                            // Redirect to search results or show results
                            console.log('Visual search results:', data);
                        }, 1000);
                    } else {
                        showToast('No similar books found. Try a different image.', 'error');
                    }
                })
                .catch(error => {
                    modal.classList.remove('show');
                    showToast('Error processing image. Please try again.', 'error');
                });
            } else {
                showToast('Please select a valid image file.', 'error');
            }
        }
    }

    // Smooth scroll navigation
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                const offsetTop = target.offsetTop - 80; // Account for fixed navbar
                window.scrollTo({
                    top: offsetTop,
                    behavior: 'smooth'
                });
            }
        });
    });

    // Carousel auto-scroll enhancement
    const carousel = document.querySelector('#bookCarousel');
    if (carousel) {
        let autoScrollInterval;

        function startAutoScroll() {
            autoScrollInterval = setInterval(() => {
                const activeItem = carousel.querySelector('.carousel-item.active');
                const nextItem = activeItem.nextElementSibling || carousel.querySelector('.carousel-item:first-child');
                if (nextItem) {
                    const bsCarousel = new bootstrap.Carousel(carousel);
                    bsCarousel.next();
                }
            }, 4000); // Auto-scroll every 4 seconds
        }

        function stopAutoScroll() {
            clearInterval(autoScrollInterval);
        }

        // Start auto-scroll on load
        startAutoScroll();

        // Pause on hover
        carousel.addEventListener('mouseenter', stopAutoScroll);
        carousel.addEventListener('mouseleave', startAutoScroll);
    }

    // Enhanced search with autocomplete
    const searchInput = document.querySelector('input[name="q"]');
    if (searchInput) {
        let suggestions = [];
        searchInput.addEventListener('input', function() {
            const query = this.value.toLowerCase();
            if (query.length < 2) {
                hideSuggestions();
                return;
            }

            // Mock autocomplete - in real app, fetch from API
            fetch('/api/book_list/')
            .then(response => response.json())
            .then(data => {
                suggestions = data.results ? data.results.filter(book =>
                    book.title.toLowerCase().includes(query) ||
                    book.author.toLowerCase().includes(query)
                ).slice(0, 5) : [];
                showSuggestions(suggestions);
            })
            .catch(() => {
                // Fallback to empty suggestions
                showSuggestions([]);
            });
        });

        function showSuggestions(suggestions) {
            hideSuggestions();
            if (suggestions.length === 0) return;

            const suggestionsDiv = document.createElement('div');
            suggestionsDiv.className = 'suggestions';
            suggestionsDiv.style.cssText = `
                position: absolute;
                top: 100%;
                left: 0;
                right: 0;
                background: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                z-index: 1000;
                max-height: 200px;
                overflow-y: auto;
                animation: fadeInUp 0.3s ease;
            `;

            suggestions.forEach(book => {
                const suggestion = document.createElement('div');
                suggestion.style.cssText = `
                    padding: 12px 15px;
                    cursor: pointer;
                    border-bottom: 1px solid #eee;
                    transition: all 0.2s ease;
                `;
                suggestion.innerHTML = `<strong>${book.title}</strong> by ${book.author}`;
                suggestion.addEventListener('click', () => {
                    searchInput.value = book.title;
                    hideSuggestions();
                    searchInput.closest('form').submit();
                });
                suggestion.addEventListener('mouseover', () => {
                    suggestion.style.background = '#f8f9fa';
                    suggestion.style.transform = 'translateX(5px)';
                });
                suggestion.addEventListener('mouseout', () => {
                    suggestion.style.background = 'white';
                    suggestion.style.transform = 'translateX(0)';
                });
                suggestionsDiv.appendChild(suggestion);
            });

            searchInput.parentNode.style.position = 'relative';
            searchInput.parentNode.appendChild(suggestionsDiv);
        }

        function hideSuggestions() {
            const existing = document.querySelector('.suggestions');
            if (existing) {
                existing.style.animation = 'fadeOut 0.2s ease';
                setTimeout(() => existing.remove(), 200);
            }
        }

        document.addEventListener('click', function(e) {
            if (!searchInput.contains(e.target) && !e.target.closest('.suggestions')) {
                hideSuggestions();
            }
        });
    }

    // Image lazy loading with fade-in
    const images = document.querySelectorAll('img[data-src]');
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.style.opacity = '0';
                img.src = img.dataset.src;
                img.onload = () => {
                    img.style.transition = 'opacity 0.5s ease';
                    img.style.opacity = '1';
                };
                img.classList.remove('lazy');
                observer.unobserve(img);
            }
        });
    });

    images.forEach(img => imageObserver.observe(img));

    // Enhanced toast notifications
    function showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast-notification ${type === 'error' ? 'error' : ''}`;
        toast.textContent = message;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('hide');
            setTimeout(() => {
                if (toast.parentNode) {
                    document.body.removeChild(toast);
                }
            }, 300);
        }, 3000);
    }

    // Create visual search modal
    function createVisualSearchModal() {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content">
                <h3 style="text-align: center; margin-bottom: 20px; color: #1B263B;">Visual Book Search</h3>
                <div class="upload-zone">
                    <i class="fas fa-cloud-upload-alt fa-3x"></i>
                    <p style="margin: 15px 0; font-weight: 500;">Drag & drop an image or click to browse</p>
                    <small style="color: #666;">Supported formats: JPG, PNG, GIF</small>
                </div>
                <input type="file" id="modal-visual-search" accept="image/*" style="display: none;">
                <div style="text-align: center; margin-top: 20px;">
                    <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').classList.remove('show')">Cancel</button>
                </div>
            </div>
        `;

        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('show');
            }
        });

        return modal;
    }

    // Intersection Observer for scroll-triggered animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.animationPlayState = 'running';
            }
        });
    }, observerOptions);

    // Observe elements for scroll animations
    document.querySelectorAll('.book-card, .category-card, .recommendation-card').forEach(card => {
        observer.observe(card);
    });
});

function getCSRFToken() {
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];
    return cookieValue || '';
}

// Pagination enhancement with loading animation
function loadPage(page) {
    const progressBar = document.querySelector('.progress-bar-loader') || document.createElement('div');
    if (!document.querySelector('.progress-bar-loader')) {
        progressBar.className = 'progress-bar-loader';
        document.body.appendChild(progressBar);
    }
    progressBar.style.display = 'block';

    const url = new URL(window.location);
    url.searchParams.set('page', page);

    setTimeout(() => {
        window.location.href = url.toString();
    }, 300);
}
