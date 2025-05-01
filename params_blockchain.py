import pandas as pd
import numpy as np
import json
from sklearn import preprocessing
from sklearn.metrics import confusion_matrix
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from flask import Flask, Response, request, jsonify
from web3 import Web3, HTTPProvider, EthereumTesterProvider
from solcx import install_solc, compile_source

install_solc(version='latest')

df = pd.read_csv('uci_malware_detection.csv')


y = df["Label"]
X = df.drop("Label", axis=1)

X_train, X_test, y_train, y_test= train_test_split(X,y, test_size=0.2, random_state=42)

w3 = Web3(EthereumTesterProvider())
w3.is_connected()

compiled_sol = compile_source(
    '''
    pragma solidity >0.5.0;

    contract ModelParameters {
        string public encoded;

        constructor() public {
            encoded = '';
        }

        function setModelParameters(string memory _encoded) public {
            encoded = _encoded;
        }

        function getModelParameters() view public returns (string memory) {
            return encoded;
        }
    }
    ''',
    output_values=['abi', 'bin']
)

contract_id, contract_interface = compiled_sol.popitem()
bytecode = contract_interface['bin']
abi = contract_interface['abi']

ModelParameters = w3.eth.contract(abi=abi, bytecode=bytecode)

tx_hash = ModelParameters.constructor().transact()
tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

ml_contract = w3.eth.contract(
    address=tx_receipt.contractAddress,
    abi=abi
)

cls = LogisticRegression()
cls.fit(X_train,y_train)

predictions = cls.predict(X_test);

accuracy = np.sum(predictions == y_test) / y_test.shape[0] * 100
conf_matrix = confusion_matrix(predictions, y_test)
precision = conf_matrix[0,0] / (conf_matrix[0,0] + conf_matrix[0,1]) * 100

print(conf_matrix)
print("Accuracy: {0:.6f}%".format(accuracy))
print("Precision: {0:.6f}%".format(precision))

encoded = json.dumps((cls.coef_.tolist(), cls.intercept_.tolist(), cls.classes_.tolist()))

w3.eth.defaultAccount = w3.eth.accounts[0]

tx_hash = ml_contract.functions.setModelParameters(encoded).transact()

tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
w3.eth.defaultAccount = w3.eth.accounts[1]

encoded_parameters = ml_contract.functions.getModelParameters().call()

decoded_parameters = json.loads(encoded_parameters)
cls_global = LogisticRegression()

cls_global.coef_ = np.array(decoded_parameters[0])
cls_global.intercept_ = np.array(decoded_parameters[1])
cls_global.classes_ = np.array(decoded_parameters[2])

predictions = cls_global.predict(X_test);
result = pd.DataFrame(np.vstack((predictions, y_test)).T,columns=['Predicted Outcomes','Actual Outcomes'])
accuracy = np.sum(predictions == y_test) / y_test.shape[0] * 100
conf_matrix = confusion_matrix(predictions, y_test)
precision = conf_matrix[0,0] / (conf_matrix[0,0] + conf_matrix[0,1]) * 100

print(conf_matrix)
print("Accuracy: {0:.6f}%".format(accuracy))
print("Precision: {0:.6f}%".format(precision))
