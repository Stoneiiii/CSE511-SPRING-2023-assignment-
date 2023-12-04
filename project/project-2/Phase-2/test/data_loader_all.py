import pyarrow.parquet as pq
import pandas as pd
from neo4j import GraphDatabase
import time


class DataLoader:

    def __init__(self, uri, user, password):
        """
        Connect to the Neo4j database and other init steps
        
        Args:
            uri (str): URI of the Neo4j database
            user (str): Username of the Neo4j database
            password (str): Password of the Neo4j database
        """
        self.driver = GraphDatabase.driver(uri, auth=(user, password), encrypted=False)
        self.driver.verify_connectivity()


    def close(self):
        """
        Close the connection to the Neo4j database
        """
        self.driver.close()


    # Define a function to create nodes and relationships in the graph
    def load_transform_file(self, file_path):
        """
        Load the parquet file and transform it into a csv file
        Then load the csv file into neo4j

        Args:
            file_path (str): Path to the parquet file to be loaded
        """

        # Read the parquet file
        trips = pq.read_table(file_path)
        trips = trips.to_pandas()

        # Some data cleaning and filtering
        trips = trips[['tpep_pickup_datetime', 'tpep_dropoff_datetime', 'PULocationID', 'DOLocationID', 'trip_distance', 'fare_amount']]

        # Filter out trips that are not in bronx


        # Convert date-time columns to supported format
        trips['tpep_pickup_datetime'] = pd.to_datetime(trips['tpep_pickup_datetime'], format='%Y-%m-%d %H:%M:%S')
        trips['tpep_dropoff_datetime'] = pd.to_datetime(trips['tpep_dropoff_datetime'], format='%Y-%m-%d %H:%M:%S')
        
        # Convert to csv and store in the current directory
        save_loc = "/var/lib/neo4j/import/" + file_path.split(".")[0] + '.csv'
        trips.to_csv(save_loc, index=False)

        # TODO: Your code here
        #create node


        load_cvs_PU = """
                LOAD CSV WITH HEADERS FROM 'file:///yellow_tripdata_2022-03.csv' AS row
                MERGE (:Location {name: toInteger(row.PULocationID)})
        """

        load_cvs_DO = """
                LOAD CSV WITH HEADERS FROM 'file:///yellow_tripdata_2022-03.csv' AS row
                MERGE (:Location {name: toInteger(row.DOLocationID)})
        """

        load_cvs_rela = """
                LOAD CSV WITH HEADERS FROM 'file:///yellow_tripdata_2022-03.csv' AS row
                MATCH (l1:Location {name: toInteger(row.PULocationID)}),(l2:Location {name: toFloat(row.DOLocationID)})
                MERGE (l1)-[r:TRIP {distance: toFloat(row.trip_distance), fare: toFloat(row.fare_amount), pickup_dt: datetime(replace(row.tpep_pickup_datetime," ","T")), 
                dropoff_dt: datetime(replace(row.tpep_dropoff_datetime," ","T"))}]
                ->(l2);
        """


        with self.driver.session() as session:
            session.run(load_cvs_PU).data()
            session.run(load_cvs_DO).data()
            session.run(load_cvs_rela).data()


def main():

    total_attempts = 10
    attempt = 0

    # The database takes some time to starup!
    # Try to connect to the database 10 times
    while attempt < total_attempts:
        try:
            data_loader = DataLoader("neo4j://localhost:7687", "neo4j", "project2phase1")
            data_loader.load_transform_file("yellow_tripdata_2022-03.parquet")
            data_loader.close()
            
            attempt = total_attempts

        except Exception as e:
            print(f"(Attempt {attempt+1}/{total_attempts}) Error: ", e)
            attempt += 1
            time.sleep(10)


if __name__ == "__main__":
    main()
