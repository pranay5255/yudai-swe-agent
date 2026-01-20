const Mutation = require('../../mutation');

/**
 * SCECOperator is a mutation testing operator designed to perform casting mutations on contract call expressions.
 * 
 * **Purpose**:
 * The operator tests how the contract behaves when casting expressions in contract calls are replaced with other contract types. This helps evaluate if different cast values affect the contract’s behavior and correctness.
 * 
 * **How It Works**:
 * 1. **Identify User-Defined Contracts**: The script first identifies user-defined contract types from the variable declarations.
 * 2. **Locate Contract Casting Expressions**: It then locates variable declarations that cast values to these contract types.
 * 3. **Perform Casting Mutations**: For each casting expression found, it replaces the original cast value with other cast values found in the same scope.
 * 4. **Create Mutation Instances**: The mutations, which consist of replacing casting values, are added to a list for testing and further analysis.
 */

function SCECOperator() {
  this.ID = "SCEC";
  this.name = "switch-call-expression-casting";
}

SCECOperator.prototype.getMutations = function (file, source, visit) {
  const mutations = [];
  let contracts = [];
  let casts = [];
  let prevRange;

  // Visit and save all user-defined contract declarations
  visit({
    VariableDeclaration: (node) => {
      if (node.typeName.type === "UserDefinedTypeName") {
        if (prevRange !== node.range) {
          if (!contracts.includes(node.typeName.namePath)) {
            contracts.push(node.typeName.namePath);
          }
        }
        prevRange = node.range;
      }
    }
  });

  // Function to find and mutate contract casting expressions
  function visitContractCast(callback) {
    // If there are at least two user-defined contracts
    if (contracts.length > 1) {
      visit({
        VariableDeclarationStatement: (node) => {
          // If declaration involves a user-defined contract
          if (node.initialValue && node.initialValue.expression && contracts.includes(node.initialValue.expression.name)) {
            // If it is a cast expression
            if (node.initialValue.arguments[0] && node.initialValue.arguments[0].type === "NumberLiteral" && node.initialValue.arguments[0].number.startsWith("0x")) {
              casts.push(node);
            }
          }
        }
      });
      // Proceed to mutation if there are at least two casting expressions
      if (casts.length > 1) {
        callback();
      }
    }
  }

  // Callback to mutate contract casting expressions
  function mutate() {
    let start, end;
    let startLine, endLine;
    let original, replacement;
    
    // Iterate over each casting expression to generate mutations
    casts.forEach(c1 => {
      start = c1.initialValue.arguments[0].range[0];
      end = c1.initialValue.arguments[0].range[1] + 1;

      startLine = c1.initialValue.arguments[0].loc.start.line;
      endLine = c1.initialValue.arguments[0].loc.end.line;
      original = source.slice(start, end);

      // Find a different casting value for replacement
      for (let i = 0; i < casts.length; i++) {
        replacement = casts[i].initialValue.arguments[0].number;
        if (original !== replacement) {
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, "SCEC"));
          break;
        }
      }
    });
  }

  // Start the mutation process
  visitContractCast(mutate);

  return mutations;
};

module.exports = SCECOperator;
