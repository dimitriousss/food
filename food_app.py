import tkinter as tk
from tkinter import messagebox
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import warnings

warnings.filterwarnings('ignore')

class Food:
    def __init__(self, df):
        self.df = df
        self.it = None
    
    def choose_cuisine(self, cuisine):
        self.it = self.df[self.df['tags'].str.contains(cuisine.replace(" ", "-"), case=False, na=False)]
        
        try:
            self.it[['calories', 'total fat (PDV)', 'sugar (PDV)', 'sodium (PDV)', 'protein (PDV)', 'saturated fat (PDV)', 'carbohydrates (PDV)']] = self.it['nutrition'].str.split(",", expand=True) 
            self.it['calories'] = self.it['calories'].apply(lambda x: x.replace('[', '')) 
            self.it['carbohydrates (PDV)'] = self.it['carbohydrates (PDV)'].apply(lambda x: x.replace(']', '')) 
            self.it[['calories','total fat (PDV)','sugar (PDV)','sodium (PDV)','protein (PDV)','saturated fat (PDV)','carbohydrates (PDV)']] = self.it[['calories','total fat (PDV)','sugar (PDV)','sodium (PDV)','protein (PDV)','saturated fat (PDV)','carbohydrates (PDV)']].astype('float')

            nb_rating_it = self.it.groupby(['recipe_id']).size().reset_index(name='number_of_raters')
            prior_weight = nb_rating_it['number_of_raters'].mean().round(0)

            avg_rating_it = self.it.groupby(['recipe_id', 'rating']).size().reset_index(name='count')
            prior_mean = self.it['rating'].mean()
            avg_rating_it['weighted_rating'] = avg_rating_it['rating'] * avg_rating_it['count']
            bayesian_avg_df = avg_rating_it.groupby('recipe_id').apply(
                lambda x: (x['weighted_rating'].sum() + (prior_mean * prior_weight)) / (x['count'].sum() + prior_weight)
            ).reset_index(name='bayesian_avg_rating').sort_values('bayesian_avg_rating', ascending=False)
            bayesian_avg_df = pd.merge(bayesian_avg_df, self.it, on='recipe_id', how='left')
            bayesian_avg_df = bayesian_avg_df[['recipe_id', 'name', 'bayesian_avg_rating']].drop_duplicates()
            bayesian_avg_df = pd.merge(bayesian_avg_df, nb_rating_it, on='recipe_id', how='left')

            bayesian_avg_df['url'] = 'https://www.food.com/recipe/' + bayesian_avg_df['name'].str.replace(" ", "-", regex=False) + '-' + bayesian_avg_df['recipe_id'].astype(str)

            bayesian_avg_df = bayesian_avg_df[['name', 'url', 'number_of_raters', 'bayesian_avg_rating']]

            return bayesian_avg_df.head(10)
        except Exception as e:
            print(f"An error occurred: {e}")
            print("Tag is not valid. Please try another one.")
            
    def generate_url(self, row):
        recipe_id = self.it[self.it['name'] == row['name']]['recipe_id'].unique()
        recipe_id = recipe_id[0]
        return f"https://www.food.com/recipe/{row['name'].replace(' ', '-')}-{recipe_id}"

    def choose_recipe(self, recipe):
        nutr = self.it.pivot_table(columns='name', values=['total fat (PDV)', 'sugar (PDV)', 'sodium (PDV)', 'protein (PDV)', 'saturated fat (PDV)', 'carbohydrates (PDV)'])
        
        try:
            twin1 = nutr[str(recipe)]
            twin2 = nutr.corrwith(twin1)
            corr = pd.DataFrame(twin2, columns=['correlation'])
            corr_df = corr.sort_values('correlation', ascending=False).reset_index()
            corr_df = corr_df[corr_df['name'] != recipe]
            
            ten_corr_df = corr_df.head(10)
            ten_corr_df['url'] = ten_corr_df.apply(self.generate_url, axis=1)
            ten_corr_df = ten_corr_df[['name', 'url', 'correlation']].drop_duplicates()
            ten_corr_df['correlation'] = ten_corr_df['correlation'].round(10)
            ten_corr_df = ten_corr_df[corr_df.correlation < 1]
            
            return ten_corr_df
        except Exception as e:
            print(f"An error occurred: {e}")
            print('Recipe is not in the database. Please try another one.') 
            
class FoodApp:
    def __init__(self, root, df):
        self.root = root
        self.food = Food(df)
        self.root.title("Food Recommendation System")
        self.root.geometry("800x800")
        self.root.config(bg="#f8f8f8")
        
        self.custom_font = ('Arial', 12)
        self.bold_font = ('Arial', 14, 'bold')
        self.comment_font = ('Arial', 8)
        
        # calling the first page (cuisine selection)
        self.cuisine_selection_page()

    def cuisine_selection_page(self):
        # clearing the window
        for widget in self.root.winfo_children():
            widget.destroy()

        # starting page
        frame = tk.Frame(self.root, bg="#f8f8f8")
        frame.pack(pady=20, padx=20, fill='both', expand=True)

        label = tk.Label(frame, text="Enter Cuisine Type*:", font=self.bold_font, bg="#f8f8f8", fg="#333333")
        label.pack(pady=20)

        self.cuisine_entry = tk.Entry(frame, width=30, font=self.custom_font, bd=2, relief="groove")
        self.cuisine_entry.pack(pady=10)

        submit_button = tk.Button(frame, text="Submit", command=self.display_recipes, bg="#35d46c", fg="#ffffff", font=self.custom_font, bd=0, padx=10, pady=5)
        submit_button.pack(pady=10)
        
        commment_label = tk.Label(frame, text="* you can also enter tags, for example: easy, high protein, main dish, oven, comfort food", font=self.comment_font, bg="#f8f8f8", fg="#919090")
        commment_label.pack(pady=10)

    def display_recipes(self):
        # generating top 10 recipies according to user input
        cuisine = self.cuisine_entry.get()
        try:
            recipes_df = self.food.choose_cuisine(cuisine)
            if recipes_df.empty:
                messagebox.showerror("Error", "No recipes found for this cuisine.")
                return
        except:
            messagebox.showerror("Error", "An error occurred. Please try another cuisine.")
            return

        # clearing the window
        for widget in self.root.winfo_children():
            widget.destroy()
            
        # displaying top 10 recipies according to user input
        frame = tk.Frame(self.root, bg="#f8f8f8")
        frame.pack(pady=20, padx=20, fill='both', expand=True)

        label = tk.Label(frame, text=f"Top 10 Recipes for {cuisine.capitalize()}:", font=self.bold_font, bg="#f8f8f8", fg="#333333")
        label.pack(pady=20)

        for idx, row in recipes_df.iterrows():
            recipe_button = tk.Button(frame, text=row['name'], command=lambda r=row: self.display_recipe_details(r), bg="#35d46c", fg="#ffffff", font=self.custom_font, bd=0, padx=10, pady=5)
            recipe_button.pack(pady=2, expand=True)

    def display_recipe_details(self, recipe):
        # clearing the window
        for widget in self.root.winfo_children():
            widget.destroy()

        # naming the recipe user chose
        frame = tk.Frame(self.root, bg="#f8f8f8")
        frame.pack(pady=20, padx=20, fill='both', expand=True)

        label = tk.Label(frame, text=f"Recipe: {recipe['name'].capitalize()}", font=self.bold_font, bg="#f8f8f8", fg="#333333")
        label.pack(pady=10)

        # linking the recipe user chose
        link_label = tk.Label(frame, text="Link to Recipe", fg="#0066cc", cursor="hand2", bg="#f8f8f8", font=self.custom_font)
        link_label.pack(pady=5)
        link_label.bind("<Button-1>", lambda e: self.open_url(recipe['url']))

        # linking the photo of the recipe user chose (if uploaded on food.com)
        try:
            url = recipe['url']
            response = requests.get(url)
            webpage_content = response.text
            soup = BeautifulSoup(webpage_content, 'html.parser')
            image_tag = soup.find('img', {'class': 'hide-on-desktop svelte-kb6fq'})
            
            if image_tag:
                image_url = image_tag['src']
                image_url = urljoin(url, image_url)
                image_link_label = tk.Label(frame, text="Link to Picture", fg="#0066cc", cursor="hand2", bg="#f8f8f8", font=self.custom_font)
                image_link_label.pack(pady=5)
                image_link_label.bind("<Button-1>", lambda e: self.open_url(image_url))
            else:
                tk.Label(frame, text="Image not found", bg="#f8f8f8", font=self.custom_font).pack(pady=5)

        except Exception as e:
            tk.Label(frame, text="Failed to load image", bg="#f8f8f8", font=self.custom_font).pack(pady=5)
            
        # naming the top 10 recipies by nutrition value correlation
        tk.Label(frame, text="Recommendations:", font=self.bold_font, bg="#f8f8f8", fg="#333333").pack(pady=10)

        recommendations_df = self.food.choose_recipe(recipe['name'])
        for idx, rec in recommendations_df.iterrows():
            rec_button = tk.Button(frame, text=rec['name'], command=lambda r=rec: self.display_recipe_details(r), bg="#35d46c", fg="#ffffff", font=self.custom_font, bd=0, padx=10, pady=5)
            rec_button.pack(pady=2, expand=True)

    def open_url(self, url):
        import webbrowser
        webbrowser.open_new(url)

# initializating data
inter = pd.read_csv('C:/Users/PlaySpace/Desktop/projects/main_projects/food/RAW_interactions.csv')
recip = pd.read_csv('C:/Users/PlaySpace/Desktop/projects/main_projects/food/RAW_recipes.csv')

inter = inter[['recipe_id', 'user_id', 'rating', 'review']]
recip['recipe_id'] = recip['id']
recip = recip[['recipe_id', 'name', 'minutes', 'nutrition', 'ingredients', 'tags']]

df = pd.merge(inter, recip, on='recipe_id', how='inner')

# running the app
root = tk.Tk()
app = FoodApp(root, df)
root.mainloop()