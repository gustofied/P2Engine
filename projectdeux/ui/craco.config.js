// craco.config.js
const path = require("path");

module.exports = {
  webpack: {
    configure: (webpackConfig) => {
      const oneOfRule = webpackConfig.module.rules.find((rule) => rule.oneOf);
      if (oneOfRule) {
        const jsRule = oneOfRule.oneOf.find(
          (rule) =>
            rule.test &&
            rule.test.toString().includes("js|mjs|jsx|ts|tsx") &&
            rule.exclude &&
            rule.exclude.toString().includes("node_modules")
        );

        if (jsRule) {
          // Exclude all node_modules except react-flow-renderer
          jsRule.exclude = /node_modules\/(?!react-flow-renderer)/;

          // Include react-flow-renderer's ES module path
          const reactFlowPath = path.resolve(
            __dirname,
            "node_modules/react-flow-renderer"
          );
          jsRule.include = [jsRule.include, reactFlowPath];
        }
      }
      return webpackConfig;
    },
  },
  babel: {
    plugins: [
      "@babel/plugin-proposal-optional-chaining",
      "@babel/plugin-proposal-nullish-coalescing-operator",
      "@babel/plugin-proposal-class-properties",
      "@babel/plugin-proposal-private-methods",
      "@babel/plugin-proposal-private-property-in-object",
    ],
  },
};
