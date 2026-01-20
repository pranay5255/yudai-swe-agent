const Mutation = require('../../mutation');

/**
 * GVROperator is a mutation testing operator designed to mutate global variables in Solidity smart contracts.
 * 
 * **Purpose**:
 * This operator tests the impact of replacing global variables with other global variables. It aims to evaluate how different global variables affect the contract's behavior and security.
 * 
 * **How It Works**:
 * 1. **Identifies Global Variable Usages**: Searches for member access expressions and identifiers in the Solidity contract that match specific global variables.
 * 2. **Generates Mutations**:
 *    - Replaces occurrences of global variables with other related global variables.
 * 
 * **Mutation Details**:
 * - **MemberAccess**:
 *   - For `msg.value`, it replaces it with `tx.gasprice`.
 *   - For `block.difficulty`, it replaces it with `block.number`, `block.timestamp`, `block.gaslimit`, `tx.gasprice`, `gasleft()`, `msg.value`.
 *   - For `block.number`, it replaces it with `block.difficulty`, `block.timestamp`, `block.gaslimit`, `tx.gasprice`, `gasleft()`, `msg.value`.
 *   - For `block.timestamp`, it replaces it with `block.number`, `block.difficulty`, `block.gaslimit`, `tx.gasprice`, `gasleft()`, `msg.value`.
 *   - For `block.coinbase`, it replaces it with `tx.origin`, `msg.sender`.
 *   - For `block.gaslimit`, it replaces it with `tx.gasprice`, `gasleft()`, `block.number`, `block.difficulty`, `block.timestamp`, `msg.value`.
 *   - For `tx.gasprice`, it replaces it with `gasleft()`, `block.gaslimit`, `block.number`, `block.difficulty`, `block.timestamp`, `msg.value`.
 * - **FunctionCall**:
 *   - For `gasleft()`, it replaces it with `tx.gasprice`, `block.gaslimit`, `block.number`, `block.difficulty`, `block.timestamp`, `msg.value`.
 *   - For `blockhash()`, it replaces it with `msg.sig`.
 * - **Identifier**:
 *   - For `now` (alias for `block.timestamp`), it replaces it with `block.difficulty`, `block.number`, `block.gaslimit`, `msg.value`, `tx.gasprice`, `gasleft()`.
 */

function GVROperator() {
  this.ID = "GVR";
  this.name = "global-variable-replacement";
}

GVROperator.prototype.getMutations = function (file, source, visit) {
  const ID = this.ID;
  const mutations = [];

  visit({
    MemberAccess: (node) => {
      const keywords = ['timestamp', 'number', 'gasLimit', 'difficulty', 'gasprice', 'value', 'blockhash', 'coinbase'];
      if (keywords.includes(node.memberName)) {
        const start = node.range[0];
        const end = node.range[1] + 1;
        const startLine = node.loc.start.line;
        const endLine = node.loc.end.line;
        const original = source.slice(start, end);

        // Handle msg.value case
        if (node.memberName === 'value' && node.expression.name === 'msg') {
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'tx.gasprice', ID));
        } 
        // Handle block.* cases
        else if (node.expression.name === 'block') {
          switch (node.memberName) {
            case 'difficulty':
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'block.number', ID));
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'block.timestamp', ID));
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'block.gaslimit', ID));
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'tx.gasprice', ID));
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'gasleft()', ID));
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'msg.value', ID));
              break;
            case 'number':
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'block.difficulty', ID));
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'block.timestamp', ID));
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'block.gaslimit', ID));
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'tx.gasprice', ID));
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'gasleft()', ID));
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'msg.value', ID));
              break;
            case 'timestamp':
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'block.number', ID));
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'block.difficulty', ID));
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'block.gaslimit', ID));
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'tx.gasprice', ID));
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'gasleft()', ID));
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'msg.value', ID));
              break;
            case 'coinbase':
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'tx.origin', ID));
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'msg.sender', ID));
              break;
            case 'gaslimit':
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'tx.gasprice', ID));
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'gasleft()', ID));
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'block.number', ID));
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'block.difficulty', ID));
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'block.timestamp', ID));
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'msg.value', ID));
              break;
          }
        } 
        // Handle tx.gasprice case
        else if (node.expression.name === 'tx' && node.memberName === 'gasprice') {
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'gasleft()', ID));
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'block.gaslimit', ID));
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'block.number', ID));
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'block.difficulty', ID));
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'block.timestamp', ID));
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'msg.value', ID));
        }
      }
    },
  });

  visit({
    FunctionCall: (node) => {
      const start = node.range[0];
      const end = node.range[1] + 1;
      const startLine = node.loc.start.line;
      const endLine = node.loc.end.line;
      const original = source.slice(start, end);
      if (node.expression.name) {
        if (node.expression.name === 'gasleft') {
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'tx.gasprice', ID));
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'block.gaslimit', ID));
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'block.number', ID));
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'block.difficulty', ID));
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'block.timestamp', ID));
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'msg.value', ID));
        } else if (node.expression.name === 'blockhash') {
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'msg.sig', ID));
        }
      }
    },
  });

  visit({
    Identifier: (node) => {
      // Alias for block.timestamp
      if (node.name === 'now') {
        const start = node.range[0];
        const end = node.range[1] + 1;
        const startLine = node.loc.start.line;
        const endLine = node.loc.end.line;
        const original = source.slice(start, end);
        mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'block.difficulty', ID));
        mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'block.number', ID));
        mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'block.gaslimit', ID));
        mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'msg.value', ID));
        mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'tx.gasprice', ID));
        mutations.push(new Mutation(file, start, end, startLine, endLine, original, 'gasleft()', ID));
      }
    },
  });

  return mutations;
}

module.exports = GVROperator;
