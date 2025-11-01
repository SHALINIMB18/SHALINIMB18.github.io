Build a complete AI-powered online bookstore called **BiblioTrack** that provides intelligent book discovery, visual and semantic search, personalized AI recommendations, a real-time Book Club, chatbot assistant, in-app notifications, and a secure purchasing system with a Buy Now button.

🎯 Objective:
Create an advanced Django-based bookstore that uses AI + ML to enhance user experience, discovery, and purchases in one unified platform.

---

### ⚙️ Tech Stack
- **Frontend:** HTML, CSS, JavaScript
- **Backend:** Django
- **Database:** SQLite 
- **AI & ML:** Sentence-BERT, Scikit-learn, TensorFlow, OpenCV
- **Real-time:** Django Channels + Redis
- **Payment Gateway:** Razorpay (Test Mode)
- **Deployment:** Render / Azure / Docker-ready

---

### 🚀 Key Features

#### 👤 1. User Management
- Register, Login, Logout using Django Auth.
- User profile with reading preferences, wishlist, and order history.

---

#### 📚 2. Book Management
- Admin can Add/Edit/Delete books.
- Each book includes: Title, Author, Genre, Description, Tags, Price, Stock, and Image.
- Books displayed by category and popularity.

---

#### 🔍 3. Semantic Search
- Use **Sentence-BERT** to find books by **meaning**, not just keywords.
- Example: Searching “inspiring biographies” returns books related to life stories, even if “inspiring” isn’t in the title.

---

#### 🖼️ 4. Visual Search
- Allow users to upload an image of a book cover.
- Use **TensorFlow + OpenCV** to identify visually similar books.
- Feature extraction via pre-trained ResNet/MobileNet models.

---

#### 🤖 5. AI Recommendation Engine
- **Hybrid system:** Content-based + Collaborative filtering.
- Analyzes user ratings, genre preferences, and purchases.
- Displays a personalized "Recommended for You" section on Home Page.

---

#### 💬 6. Book Club
- Real-time discussion thread for each book.
- Readers can post reviews, like, reply, and share opinions.
- Built using **Django Channels** for live updates.

---

#### 💁 7. Chatbot Assistant
- Built-in AI chatbot for:
  - Book recommendations
  - Payment/order assistance
  - Navigation help
- Simple NLP-based intent classifier or integration with Dialogflow.

---

#### 🔔 8. In-App Notifications
- Notifications for:
  - New comments/replies in Book Club
  - Order updates (Placed → Shipped → Delivered)
  - Personalized AI recommendations
- Implemented via WebSockets (Django Channels).

---

#### 🛒 9. Shopping Cart & **Buy Now Button**
- Each book page includes two buttons:
  - **🛒 Add to Cart** → Adds item to shopping cart.
  - **💳 Buy Now** → Directly opens checkout page for that single book.
- When user clicks **Buy Now**:
  1. The book details (ID, title, price) are passed to the checkout view.
  2. User confirms address and payment.
  3. Order is created and sent to Razorpay API.
  4. After successful payment:
     - Order status is updated to *Confirmed*.
     - Invoice is generated (PDF).
     - User receives in-app notification and email confirmation.
- **Order status workflow:**

**10.Create a Django-based Wishlist :

-Add to wishlist, remove, view, and move to cart features

-A user-specific wishlist model

-Wishlist page with book images and buttons

-Integration with the existing book catalog

Simple responsive HTML + CSS design for wishlist display

-AI recommendations based on wishlist items using cosine similarity between book genres or descriptions.”

---

#### 💳 11. Payment Integration
- Razorpay integration with API keys (Test Mode).
- Backend verifies payment signature.
- On success:
- Store transaction in database.
- Generate downloadable invoice.
- Notify user via WebSocket and email.

---

#### 🧮 12. Admin Dashboard
- Manage all books, users, and orders.
- Visual analytics on sales and active book clubs.
- Export data (CSV or PDF).

---

### 🧩 AI / ML Modules Used

| Feature | Algorithm/Model | Description |
|----------|----------------|--------------|
| Semantic Search | Sentence-BERT | Finds similar books based on meaning |
| Recommendations | Collaborative + Content-based | Personalized book suggestions |
| Visual Search | TensorFlow + OpenCV | Find books by image similarity |
| Chatbot | NLP Intent Classifier | Helps users navigate and discover |
| Notifications | Django Channels + Redis | Real-time user engagement |
| Buy Button Flow | Razorpay API | Secure order and payment handling |

---

### 📂 Dataset (books.csv)

### ✅ Completed Tasks
- [x] Installed required AI/ML dependencies (sentence-transformers, tensorflow, opencv-python, torch)
- [x] Updated requirements.txt with new dependencies
- [x] Trained recommendation model successfully
- [x] Precomputed features for books (0 books processed - likely no data yet)
- [x] Django server running at http://127.0.0.1:8000/
- [x] Browser tool disabled - need to enable in VSCode settings for full testing
- [x] Added BookRecommendation model for storing personalized book recommendations

### 🔄 Next Steps
- [x] Enable browser tool in VSCode settings.json
- [x] Populate database with sample books (99 books added)
- [ ] Test semantic search functionality
- [ ] Test visual search functionality
- [ ] Test AI recommendations
- [ ] Test chatbot assistant
- [ ] Test wishlist features
- [ ] Test shopping cart and buy now functionality
- [ ] Test payment integration with Razorpay
- [ ] Test book club real-time features
- [ ] Test in-app notifications

