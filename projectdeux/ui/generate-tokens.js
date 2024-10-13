const jwt = require("jsonwebtoken");

const token = jwt.sign(
  {
    "https://daml.com/ledger-api": {
      ledgerId: "sandbox",
      applicationId: "my-app",
      actAs: [
        "Alice::12202ed475a768f08e2253eccd8a78b9e78cddec352438f28c51d7cca35e15809422",
      ],
    },
  },
  "secret", // Use 'secret' as the signing key for development
  { algorithm: "HS256" }
);

console.log(token);
