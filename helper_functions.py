import pandas as pd
import os
import glob
import re

def get_current_price_by_name(stock_name):
    """
    Takes a stock name, finds its ID, locates its price file, 
    and returns the latest closing price.
    """
    # 1. Convert to lower case
    search_name = stock_name.lower()
    
    # 2. Load the stock master list to find the ID
    stocks_df = pd.read_csv("data/stocks.csv")
    
    # Search for the stock name in the company_name column (case-insensitive)
    # We check for exact match first, then fallback to partial match
    match = stocks_df[stocks_df["company_name"].str.lower() == search_name]
    
    if match.empty:
        # Fallback to partial match if exact match fails
        match = stocks_df[stocks_df["company_name"].str.lower().str.contains(search_name)]
        
    if match.empty:
        print(f"Stock '{stock_name}' not found in master list.")
        return None
    
    # Get the ID (handling potential multiple matches by taking the first one)
    stock_id = match.iloc[0]["stock_id"]
    
    # 3. Locate the price file based on the ID
    price_dir = "data/prices"
    # The pattern is {id}_{nameofstock}.csv
    search_pattern = os.path.join(price_dir, f"{stock_id}_*.csv")
    matching_files = glob.glob(search_pattern)
    
    if not matching_files:
        print(f"Price file for stock ID {stock_id} not found in {price_dir}.")
        return None
    
    # Take the first matching file
    price_file = matching_files[0]
    
    # 4. Fetch the latest price from the CSV
    try:
        price_df = pd.read_csv(price_file)
        
        if price_df.empty:
            print(f"Price file {price_file} is empty.")
            return None
        
        # In yfinance CSVs, the close price column is 'Close'
        latest_price = price_df.iloc[-1]["Close"]
        return float(latest_price)
        
    except Exception as e:
        print(f"Error reading price file {price_file}: {e}")
        return None

# Example usage (commented out)
if __name__ == "__main__":
    price = get_current_price_by_name("ABB India")
    print(f"Latest Price: {price}")
