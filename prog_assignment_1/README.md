# Programming Assignment 1: AWS IAM and S3 Management with Boto3

This project contains a Python script that uses the AWS SDK for Python (Boto3) to manage IAM roles, users, and S3 resources. It also includes a test suite that uses `moto` to mock AWS services, allowing the script to be tested without needing live AWS credentials.

## Features

- **IAM Role Creation**: Creates two IAM roles, `Dev` and `User`, with different levels of access to S3.
- **IAM User Creation**: Creates a new IAM user.
- **S3 Resource Management**:
  - Assumes the `Dev` role to create a uniquely named S3 bucket.
  - Uploads three files (`assignment1.txt`, `assignment2.txt`, `recording1.jpg`) to the bucket.
- **S3 Data Processing**:
  - Assumes the `User` role to list objects with a specific prefix (`assignment`).
  - Computes the total size of the filtered objects.
- **Resource Cleanup**: Assumes the `Dev` role to delete all objects and the S3 bucket.
- **Testable**: The script is designed to be testable, and it comes with a comprehensive test suite using `pytest` and `moto`.

## Prerequisites

- Python 3.8+
- `pip` for installing packages

## Setup and Execution

1.  **Clone the repository and navigate to the project directory.**

2.  **Install the required Python packages:**

    ```bash
    pip install -r requirements.txt
    ```

    *(Note: A `requirements.txt` file would typically be included. For this project, you can install the dependencies manually as listed below.)*

3.  **Install dependencies manually:**

    ```bash
    pip install boto3 pytest "moto[iam,s3]"
    ```

4.  **Run the tests:**

    To verify that the script's logic is correct, you can run the test suite. The tests use `moto` to simulate AWS services, so no real AWS credentials are required.

    ```bash
    PYTHONPATH=. pytest prog_assignment_1/test_assignment.py
    ```

5.  **Run the script (with AWS Credentials):**

    To run the script against a real AWS account, you must first configure your AWS credentials. You can do this by:
    - Running `aws configure` in your terminal and providing your credentials.
    - Setting the `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_SESSION_TOKEN` (if applicable) environment variables.

    Once your credentials are set up, you can execute the script:

    ```bash
    python prog_assignment_1/assignment.py
    ```

    The script will print its progress to the console as it creates, manages, and cleans up AWS resources.