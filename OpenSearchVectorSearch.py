from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from langchain_openai import OpenAIEmbeddings
import os
import requests

class OpenSearchVectorSearch:
    def __init__(self, OPENSEARCH_URL, OPENSEARCH_PORT, OPENSEARCH_USERNAME, OPENSEARCH_PASSWORD):
        self.OPENSEARCH_URL = OPENSEARCH_URL
        self.OPENSEARCH_PORT = OPENSEARCH_PORT
        self.OPENSEARCH_USERNAME = OPENSEARCH_USERNAME
        self.OPENSEARCH_PASSWORD = OPENSEARCH_PASSWORD

    def get_opensearch_client(self):

        # creating the client with SSL/TLS enabled
        client = OpenSearch(
            hosts=[{"host": "localhost", "port": self.OPENSEARCH_PORT}],
            http_auth=(self.OPENSEARCH_USERNAME, self.OPENSEARCH_PASSWORD),
            use_ssl=True,
            verify_certs=False,
            connection_class=RequestsHttpConnection,
            timeout=300
        )
        print("OpenSearch client created successfully....!")
        return client
    
    def embed_query(self, query):
        embedding_model = OpenAIEmbeddings(
            model="text-embedding-ada-002"
        )
        embedding = embedding_model.embed_query(query)
        return embedding

    def similarity_search(self, index_name, query, top_k):
        client = self.get_opensearch_client()
        embeded_query = self.embed_query(query)
        query = {
            "_source": {
                "exclude": [
                        "vector_field"
                ]
                 },
            "query": {
                "knn": {
                    "vector_field": {
                        "vector": embeded_query,
                        "k": top_k
                    }
                }
            }
        }
        results = client.search(index=index_name, 
                                body=query)
        return results["hits"]["hits"] 
    

    def keyword_search(self, index_name, query, top_k):
        client = self.get_opensearch_client()
        query = {
            "_source": {
                "exclude": [
                        "vector_field"
                ]
                 },
            "query": {
                "match": {
                    "text": query
                }
            },
            "size": top_k
        }
        results = client.search(index=index_name, 
                                body=query)
        return results["hits"]["hits"]

    def hybrid_search(self, query, top_k, index_name, search_pipeline_name):
        path = f"{index_name}/_search?search_pipeline={search_pipeline_name}" 
        auth = (self.OPENSEARCH_USERNAME, self.OPENSEARCH_PASSWORD)
        url = self.OPENSEARCH_URL + ":" + self.OPENSEARCH_PORT + "/" + path

        # embedding query 
        embeded_query = self.embed_query(query)

        payload = {
        "_source": {
            "exclude": [
            "vector_field"
            ]
        },
        "query": {
            "hybrid": {
            "queries": [
                {
                "match": {
                    "caption": {
                    "query": query
                    }
                }
                },
                {
                "knn": {
                    "vector_field": {
                    "vector": embeded_query,
                    "k": top_k
                    }
                }
                }
            ]
            }
        },"size":top_k
        }

        r = requests.get(url, auth=auth, json=payload, verify=False)
        results = r.json()
        return results["hits"]["hits"]

    def create_search_pipeline(self, search_pipeline_name, keyword_weight=0.5, vector_weight=0.5):
        path=f"_search/pipeline/{search_pipeline_name}"
        host = self.OPENSEARCH_URL + ":" + self.OPENSEARCH_PORT + "/"
        auth = ('admin', 'opensearch123@KB')
        url = host + path
        payload = {
        "description": "Post processor for hybrid search",
        "phase_results_processors": [
            {
            "normalization-processor": {
                "normalization": {
                "technique": "min_max"
                },
                "combination": {
                "technique": "arithmetic_mean",
                "parameters": {
                    "weights": [
                    keyword_weight,
                    vector_weight
                    ]
                }
                }
            }
            }
        ]
        }
        r = requests.put(url, auth=("admin", "opensearch123@KB"), json=payload, verify=False)
        if r.status_code == 200:
            print(f"Search pipeline {search_pipeline_name} created successfully....!")
            print(f"Response: {r.json()}")
        else:
            print(f"Error creating search pipeline {search_pipeline_name}....!")
            print(f"Response: {r.json()}")