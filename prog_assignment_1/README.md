# Programming Assignment 1: AWS IAM and S3 Management with Boto3

This project contains a Python script that uses the AWS SDK for Python (Boto3) to manage IAM roles, users, and S3 resources, as per the assignment requirements. It also includes a granular test suite that uses `moto` to mock AWS services, allowing the script to be tested without needing live AWS credentials.

The script has been structured as a Python package for robustness and includes production-ready features like region-aware bucket creation and full resource cleanup.

## Features

- **IAM Role Creation**: Creates two IAM roles, `Dev` (S3 Full Access) and `User` (S3 List/Get Access).
- **IAM User Creation**: Creates an IAM user and attaches a policy allowing it to assume the `Dev` and `User` roles.
- **S3 Resource Management**:
  - Assumes the `Dev` role to create a uniquely named S3 bucket and upload `assignment1.txt`, `assignment2.txt`, and `recording1.jpg`.
- **S3 Data Processing**:
  - Assumes the `User` role to find all objects with the prefix `assignment` and compute their total size.
- **Full Resource Cleanup**: Cleans up all created resources, including S3 objects, the S3 bucket, IAM policies, roles, and the user.
- **Granular Testing**: The `test_assignment.py` script contains specific tests for each requirement of the assignment, ensuring full coverage.

## Prerequisites

- Python 3.8+
- `pip` for installing packages

## Setup and Execution

1.  **Clone the repository and navigate to the project directory.**

2.  **Install the required Python packages:**

    ```bash
    pip install boto3 pytest "moto[iam,s3]"
    ```

3.  **Run the tests:**

    To verify that the script's logic is correct, run the test suite from the project's root directory. The tests use `moto` to simulate AWS services, so no real AWS credentials are required.

    ```bash
    pytest
    ```

    You should see output indicating that all 5 tests passed, confirming that each assignment requirement is met.

4.  **Run the script (with AWS Credentials):**

    To run the script against a real AWS account, you must first configure your AWS credentials (e.g., by running `aws configure`). Once configured, execute the script from the project root:

    ```bash
    python prog_assignment_1/assignment.py
    ```

    The script will print its progress to the console as it creates, manages, and cleans up all AWS resources.

## Project Structure Notes

-   **`__init__.py`**: This empty file inside the `prog_assignment_1/` directory marks it as a Python package, which helps prevent import errors.
-   **`pyproject.toml`**: This file is used to configure development tools like `pytest`. In this project, it tells `pytest` that the project's root directory should be included in the Python path (`pythonpath = ["."]` ), which allows it to find and run the tests without any path issues. This makes running tests as simple as typing `pytest`.