const Mutation = require('../../mutation');

/**
 * EROperator is a mutation testing operator designed to test changes in Ether transfer functions within Solidity smart contracts.
 * 
 * **Purpose**:
 * This operator generates mutations to test how modifications to Ether transfer functions affect the smart contract's behavior. It performs several types of mutations by replacing Ether transfer functions or altering their arguments.
 * 
 * **How It Works**:
 * 1. **Identifies Ether Transfer Functions**: The operator looks for function calls involving Ether transfer methods.
 * 2. **Generates Mutations**:
 *    - **Calls with Gas or Value**:
 *      - **Call Replacement**: Changes `call` to `delegatecall` or `staticcall`.
 *      - **Delegatecall Replacement**: Changes `delegatecall` to `call` or `staticcall`.
 *      - **Staticcall Replacement**: Changes `staticcall` to `call` or `delegatecall`.
 *    - **Calls Without Gas or Value**:
 *      - **Send Replacement**: Changes `send` to `transfer` or `call`.
 *      - **Transfer Replacement**: Changes `transfer` to `send` or `call`.
 * 
 * **Mutation Details**:
 * - **Call with Gas or Value**:
 *   - Modifies function calls with `gas` or `value` arguments by replacing the original function with alternative functions while preserving arguments.
 * - **Call without Gas or Value**:
 *   - Changes function calls without `gas` or `value` arguments to alternative functions, potentially altering the way Ether is sent.
 * 
 * This script helps in evaluating how changes to Ether transfer functions impact the smart contract's behavior, ensuring the contract operates correctly under different transfer scenarios.
 */

function ETROperator() {
  this.ID = "ETR";
  this.name = "ether-transfer-function-replacement";
}

ETROperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];
  const functions = ["transfer", "send", "call", "delegatecall", "staticcall"];

  visit({
    FunctionCall: (node) => {

      // Check if the function call involves an Ether transfer function
      if ((node.expression.type == "MemberAccess" || (node.expression.expression && node.expression.expression.type == "MemberAccess"))) {
        if (functions.includes(node.expression.memberName) || functions.includes(node.expression.expression.memberName)) {

          // Handle calls with gas or value arguments
          if (node.expression.expression && functions.includes(node.expression.expression.memberName)) {

            var replacement, replacement2;
            const start = node.range[0];
            const end = node.range[1] + 1;
            const startLine = node.loc.start.line;
            const endLine = node.loc.end.line;
            const original = source.slice(start, end);

            // Extract address and call arguments
            const addressStart = node.expression.expression.expression.range[0];
            const addressEnd = node.expression.expression.expression.range[1];
            const address = source.slice(addressStart, addressEnd + 1);
            const callArguments = source.slice(node.arguments[0].range[0], node.arguments[0].range[1] + 1);

            // Exclude old call() syntax
            if (node.expression.arguments) {
              const valueArguments = source.slice(node.expression.arguments.range[0], node.expression.arguments.range[1] + 1);
              if (node.expression.expression.memberName === "call") {

                const nameValueList = node.expression.arguments.names;
                var gas;
                gasIndex = nameValueList.indexOf("gas");
                if (gasIndex != -1) { // If the call has a gas argument
                  gas = node.expression.arguments.arguments[gasIndex].number;
                }

                // Generate mutations for call with gas
                replacement = address + ".delegatecall";
                replacement2 = address + ".staticcall";
                if (gas) {
                  replacement += "{gas:" + gas + "}";
                  replacement2 += "{gas:" + gas + "}";
                }
                replacement += "(" + callArguments + ")";
                replacement2 += "(" + callArguments + ")";

                mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
                mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement2, this.ID));

              } else if (node.expression.expression.memberName === "delegatecall") {

                // Generate mutations for delegatecall with value
                replacement = address + ".call" + "{" + valueArguments + "}" + "(" + callArguments + ")";
                replacement2 = address + ".staticcall" + "{" + valueArguments + "}" + "(" + callArguments + ")";

                mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
                mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement2, this.ID));

              } else if (node.expression.expression.memberName === "staticcall") {

                // Generate mutations for staticcall with value
                replacement = address + ".call" + "{" + valueArguments + "}" + "(" + callArguments + ")";
                replacement2 = address + ".delegatecall" + "{" + valueArguments + "}" + "(" + callArguments + ")";

                mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
                mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement2, this.ID));
              }
            }
          }
          // Handle calls without gas or value arguments
          else {

            var start = node.expression.range[0];
            var end = node.expression.range[1] + 1;
            var startLine = node.expression.loc.start.line;
            var endLine = node.expression.loc.end.line;
            let original = source.slice(start, end);
            let replacement, replacement2;

            // Extract address and call arguments
            const addressStart = node.expression.expression.range[0];
            const addressEnd = node.expression.expression.range[1];
            const address = source.slice(addressStart, addressEnd + 1);

            var arg;
            if (node.arguments[0]) {
              if (node.arguments[0].type === "NumberLiteral") {
                arg = node.arguments[0].number;
              } else if (node.arguments[0].type === "Identifier") {
                arg = node.arguments[0].name;
              } else if (node.arguments[0].type === "MemberAccess" || node.arguments[0].type === "FunctionCall") {
                var argStart = node.arguments[0].range[0];
                var argEnd = node.arguments[0].range[1];
                arg = source.slice(argStart, argEnd + 1);
              }
            }

            const subdenomination = node.arguments[0].subdenomination;

            // Generate mutations based on the function type
            if (node.expression.memberName == "call") {

              // Replace call with delegatecall and staticcall
              replacement = address + ".delegatecall";
              replacement2 = address + ".staticcall";

              mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement2, this.ID));
            } else if (node.expression.memberName == "delegatecall") {

              // Replace delegatecall with call and staticcall
              replacement = address + ".call";
              replacement2 = address + ".staticcall";

              mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement2, this.ID));
            } else if (node.expression.memberName == "staticcall") {

              // Replace staticcall with call and delegatecall
              replacement = address + ".call";
              replacement2 = address + ".delegatecall";

              mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement2, this.ID));
            } else if (node.expression.memberName == "send") {

              // Replace send with transfer and call
              replacement = address + ".transfer";
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));

              start = node.range[0];
              end = node.range[1] + 1;
              startLine = node.loc.start.line;
              endLine = node.loc.end.line;

              replacement2 = address + ".call{value: " + arg;
              if (subdenomination)
                replacement2 += " " + subdenomination + "}(\"\")";
              else
                replacement2 += "}(\"\")";

              mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement2, this.ID));

            } else if (node.expression.memberName == "transfer") {

              // Replace transfer with send and call
              replacement = address + ".send";
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));

              start = node.range[0];
              end = node.range[1] + 1;
              startLine = node.loc.start.line;
              endLine = node.loc.end.line;

              replacement2 = address + ".call{value: " + arg;
              if (subdenomination)
                replacement2 += " " + subdenomination + "}(\"\")";
              else
                replacement2 += "}(\"\")";
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement2, this.ID));
            }
          }
        }
      }
    }
  });
  return mutations;
};

module.exports = ETROperator;
