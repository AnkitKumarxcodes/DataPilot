import sys
import os
import requests
import pandas as pd



class ETLAgentTools:
    def __init__ (self):
        pass
    def extract_and_load(self , url:str , output_folder:str , format:str):
        """
        this tool extracts datafrom the API (url) and loads into the desired into destination

        Args:
            url(str):the API endpoint from whcich to extract data.
            Output_folder(str):The folder where the extracted data will be saved

        Returns:
            str:A message indicating the success or failure of the operation
        """

        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__) , '..'))
        output_folder = os.path.join(project_root , output_folder)

        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()["results"]
            filename = os.path.join(output_folder , f"extracted_data.{format}")
            os.makedirs(output_folder ,exist_ok=True)
            df = pd.json_normalize(data)
            if format == "csv":
                df.to_csv(filename , index = False)
            elif format == "json":
                df.to_json(filename , orient = "records" , lines = True)
            elif format == "parquet":
                df.to_parquet(filename , index = False)
            
            else:
                return f"Unsupported Format:{format}"
            return f"Data Successfully extractaed and saved to {filename}"
        except requests.exceptions.RequestException as e:
            return f"Failed to extract data: {e}"

    def transform_load_context(self , file_path:str):
        """
        This tool transforms the data from the specified file and loads it into the desired location(output folder).

        Args:
            file_path(Str):the path to the file the containing the data to be transormed 
            output_folder(Str);the folder where the transformed data will be saved 
            format(str);the format of the data(csv , parquet , json)
        Returns:
        str: A message indicating success or failure of operation
        """
        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension == ".csv":
            df = pd.read_csv(file_path)
        elif file_extension == ".json":
            df = pd.read_json(file_path , lines= True)
        elif file_extension == ".parquet":
            df = pd.read_parquet(file_path)
        else:
            return f"Unsupported file format: {file_extension}"

        top_3_rows = str(df.head(3))
        return top_3_rows

    def execute_python(self  , code:str):
        """
        This tool executes the provided code and returns the output to ReAct agent
        """

        try:
            exec(code)
            return "Code executed successfully"
        except Exception as e:
            return f"failed to execute the code: {e}"


    
if __name__ == "__main__":
    obj = ETLAgentTools()
    # print(obj.extract_and_load("https://pokeapi.co/api/v2/pokemon/" , "data/extractapi" , "csv"))
    path = "D:\\Projects\\DataPilot\\data\\extractapi\\extracted_data.csv"
    print(obj.transform_load_context(path))