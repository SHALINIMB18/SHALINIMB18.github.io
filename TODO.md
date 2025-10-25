# Training AI Recommendation Chatbot Models

## Tasks to Complete
- [ ] Install/update dependencies from requirements.txt
- [ ] Train the book recommendation model (TF-IDF + KMeans clustering)
- [ ] Precompute VGG16 features for visual search
- [ ] Test the trained models with the chatbot
- [ ] Verify chatbot handles both text questions and image inputs

## Information Gathered
- **ai_recommendation.py**: Contains `train_recommendation_model()` function that uses TF-IDF vectorization and KMeans clustering on book categories, genres, and authors
- **visual_search.py**: Uses VGG16 model for extracting image features and cosine similarity for finding similar books
- **precompute_features.py**: Django management command to precompute VGG16 features for all books with images
- **chatbot_utils.py**: Rule-based chatbot that handles text queries and integrates with visual search for images
- The chatbot can process both text questions (recommendations, search) and image uploads (visual search)

## Plan
1. Execute the recommendation model training by calling `train_recommendation_model()`
2. Run the Django management command to precompute VGG16 features for visual search
3. Test the chatbot API with both text and image inputs to verify training worked
4. Ensure all dependencies are installed (scikit-learn, tensorflow, nltk, etc.)

## Dependent Files
- bookstore_project/books/ai_recommendation.py
- bookstore_project/books/visual_search.py
- bookstore_project/books/management/commands/precompute_features.py
- bookstore_project/books/chatbot_utils.py
- bookstore_project/requirements.txt

## Followup Steps
- Install any missing dependencies if needed
- Run the Django server to test the chatbot
- Verify model files are saved correctly
