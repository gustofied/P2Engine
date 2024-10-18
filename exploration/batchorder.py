# This file serves as a template
# The goal function is to be able to trade multiple assetss with one order
# This takes from the concept of flow order, a new type of creating a trading engine, which in contrast to the normally used CLOB at CeFi.

stock1 = 10
stock2 = 100
fiat = 1000
account1 = [] # account 1 is a user account
account2 = [] # account 2 is a user account
account3 = [] # account 3 is a settlement accouont, keeps track of the accounts
# First we set account1 and account2 to hold some assets.
# account1 has a portfolio of stock1 and fiat
# account2 has a porfolio of just stock2
# to simplify we use a list, and the ordering of 0=stock1, 1=stock2 etc

account1 = [int(stock1*0.5), int(stock2*0), int(fiat*0.5)]
account2 = [int(stock1*0), int(stock2*1), int(fiat*0)]

print(account1)
print(account2)

# TODO implement matching/swapping of assets

for x in range(len(account1)):
    account1[x]=(account1[x] - account2[x])
    account2[x]=(account2[x] - account2[x])
account3 = [account1, account2]

print(account1, account2, account3)

#  Transfer Example Using Daml
# Consider the transfer example described above with Alice and Bob. Using Daml, the process looks
# like this:
# 1. 2. Alice logs into her online banking at Bank A and enters a transfer to Bob at Bank B.
# The online banking backend creates a transaction that deducts $100 from Alice’s account and
# creates a transfer to Bob at Bank B.
# 3. When Bank B accepts the transfer, Bank A credits $100 to Bank B’s account at Bank A and Bank
# B simultaneously credits Bob’s account by $100.
# 4. Bob’s online banking interfaces with the Daml Ledger and can see the incoming funds in real
# time.
# At every point, ownership of the $100 is completely clear and all systems are fully consistent.