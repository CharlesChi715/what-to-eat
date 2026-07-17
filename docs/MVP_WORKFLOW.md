# MVP Workflow

Photo → Recognition → User confirmation → Inventory → Ingredient selection → Recipe generation

Frontend: web app
Backend: my WSL2 PC.

## 1. Capture and recognize food

1. **User:** Takes photos of food or ingredient labels.
2. **Frontend:** Sends the images to the backend.
3. **Backend:** Uses an OpenAI vision model to identify the food.
4. **Frontend:** Shows the recognition results for confirmation.
5. **User:** Confirms or corrects the results.

## 2. Update inventory

1. **Backend:** Checks for possible duplicate items.
2. **Backend:** Saves confirmed foods, quantities, and expiry dates.
3. **Frontend:** Displays the updated inventory.
4. **Frontend:** Highlights items that are close to expiry.

## 3. Choose ingredients

1. **User:** Selects ingredients they want to use.
2. **Frontend:** Sends the selection to the backend.
3. **Backend:** Prioritizes ingredients that are close to expiry.

## 4. Generate a recipe

1. **Backend:** Generates suitable recipe suggestions.
2. **Frontend:** Displays the recipes.
3. **User:** Chooses a recipe to cook.