const express = require('express');
const Mutation = require('../../mutation');

function ROSOperator() {
    this.ID = "ROS";
    this.name = "reentrancy-order-swap";
}

ROSOperator.prototype.getMutations = function(file, source, visit) {
    const mutations = [];
    let lastPureEnd = -1; // Variabile per tenere traccia della fine dell'ultimo blocco 'pure'
    let events = [];
    let structContractsDefinitions = [];
    let constructorFound = false;

    visit({
        ContractDefinition: handleStructContractsDefinitions,
        StructDefinition: handleStructContractsDefinitions
    })

    visit({
        EventDefinition: handleEvent
    })

    visit({
        FunctionDefinition: handleFunctionDefinition,
        Block: handleBlockWithBody,
    });

    function handleStructContractsDefinitions(node){
        structContractsDefinitions.push(node.name);
    }

    function handleEvent(node) {
        
        events.push(node.name); // Usa push per aggiungere l'evento all'array
    }
    
    function handleFunctionDefinition(node) {
        constructorFound = false;
        if (node.isConstructor) {
            constructorFound = true;
            return;
        }

        // Verifica se la funzione è di tipo 'pure'
        if (node.stateMutability === 'pure') {
            lastPureEnd = node.range[1]; // Aggiorna lastPureEnd con l'end della funzione 'pure'
        }
    }

    function isStateModifyingExpression(statement) {
        const expression = statement.expression;
        
        if(expression.right && !expression.right.expression){
            return true;
        }

        if(expression.right.type === 'MemberAccess'){
            return true;
        }

        if (expression.right.type === 'FunctionCall') {
            
            const rightExpression = expression.right.expression;
            // Caso per le funzioni che usano MemberAccess (ad esempio, `address.transfer`, `token.balanceOf`)
            if (rightExpression.type === 'MemberAccess' &&
                (
                //rightExpression.memberName === 'transfer' ||
                // rightExpression.memberName === 'address' ||
                // rightExpression.memberName === 'send' ||
                // rightExpression.memberName === 'push' ||
                // rightExpression.memberName === 'add' ||
                // rightExpression.memberName === 'mul' ||
                // rightExpression.memberName === 'div' ||
                // rightExpression.memberName === 'sub' ||
                // rightExpression.memberName === 'balanceOf' ||
                // rightExpression.memberName === 'keccak256'
                rightExpression.memberName !== 'call'
            )
            ) {
                return true;
            }

            if(rightExpression.type === 'Identifier' && structContractsDefinitions.includes(rightExpression.name)){
                
                return true;
            }

            if (rightExpression.type === 'Identifier' &&
                (
                //rightExpression.name === 'transfer' ||
                // rightExpression.name === 'address' ||
                // rightExpression.name === 'send' ||
                // rightExpression.name === 'push' ||
                // rightExpression.name === 'add' ||
                // rightExpression.name === 'mul' ||
                // rightExpression.name === 'div' ||
                // rightExpression.name === 'sub' ||
                // rightExpression.name === 'balanceOf' ||
                // rightExpression.name === 'keccak256' ||
                // rightExpression.name === 'msg'
                rightExpression.name !== 'call'
            )
            ) {
                
                return true;
            }
            
            return false;
        }
        
        if (expression.type === "UnaryOperation") {
            const incrementDecrementOperators = ["++", "--"];
            return incrementDecrementOperators.includes(expression.operator);
        }
        
        return false;
    }

    function isNonStateChange(node) {
        if (!node) {
            return false;
        }

        if (node.type === 'FunctionCall') {
            const expression = node.expression;
            // Caso per le funzioni che usano MemberAccess (ad esempio, `address.transfer`, `token.balanceOf`)
            if (expression.type === 'MemberAccess' &&
                (
                //expression.memberName === 'transfer' ||
                // expression.memberName === 'send' ||
                // expression.memberName === 'address' ||
                // expression.memberName === 'push' ||
                // expression.memberName === 'add' ||
                // expression.memberName === 'mul' ||
                // expression.memberName === 'div' ||
                // expression.memberName === 'sub' ||
                // expression.memberName === 'balanceOf' ||
                // expression.memberName === 'keccak256' ||
                // expression.memberName === 'msg'
                expression.memberName !== 'call'
            )
            ) {
                return false;
            }

            if (expression.type === 'Identifier' &&
                (
                //expression.name === 'transfer' ||
                // expression.name === 'send' ||
                // expression.name === 'address' ||
                // expression.name === 'push' ||
                // expression.name === 'add' ||
                // expression.name === 'mul' ||
                // expression.name === 'div' ||
                // expression.name === 'sub' ||
                // expression.name === 'balanceOf' ||
                // expression.name === 'keccak256'
                expression.name !== 'call')
            ) {
                return false;
            }
        }
    
        if(node.condition){
            if(node.condition.type === 'FunctionCall'){
                return true;
            } else if (node.condition.type === 'BinaryOperation'){
                const left = node.condition.left;
                const right = node.condition.right;
                return isNonStateChange(left) || isNonStateChange(right)
            } else if (node.condition.type === 'UnaryOperation') {
                const sub = node.condition.subExpression;
                return isNonStateChange(sub);
            }
            
        }

        if(node.type === "ExpressionStatement" && node.expression.type === "BinaryOperation"){
            return !isStateModifyingExpression(node);
        }
        
        if (node.type === 'FunctionCall') {
            // Controlla se è una chiamata a assert o require
            if (node.expression.name === 'assert' || node.expression.name === 'require') {
                const args = node.arguments;
    
                // Controlla se gli argomenti esistono e sono iterabili (array o simil-array)
                if (Array.isArray(args)) {
                    // Controlla se almeno uno degli argomenti è una FunctionCall che non sia transfer o send
                    for (const arg of args) {
                        if (isNonStateChange(arg)) {
                            return true; // Restituisci true se trovi una chiamata a funzione valida
                        }
                    }
                }
                return false; // Nessuna chiamata a funzione valida trovata tra gli argomenti
            }
    
            return true; // È una FunctionCall, ma non transfer/send
        }
    
        // Esplora ricorsivamente il contenuto di expression, body, trueBody, falseBody
        if (node.expression && isNonStateChange(node.expression)) {
            return true;
        }
        
        const bodies = [node.body, node.trueBody, node.falseBody];

        for (const body of bodies) {
            // Controlla se il body esiste ed è iterabile (array o simil-array)
            if (Array.isArray(body)) {
                // Itera su ciascun elemento del body
                for (const stmt of body) {
                    if (isNonStateChange(stmt)) {
                        return true; // Restituisci true se trovi una chiamata a funzione valida nel body
                    }
                }
            } else if (body && isNonStateChange(body)) {
                return true; // Restituisci true se il body stesso è una chiamata a funzione
            }
        }
    
        return false;
    }
    

    function handleBlockWithBody(node) {
        if(constructorFound) return;
        
        // Salta l'analisi se lastPureEnd è maggiore o uguale all'end del blocco corrente
        if (node.range[1] <= lastPureEnd) {
            return; // Ignora questo blocco
        }

        if (!node.statements || !Array.isArray(node.statements)) {
            return;
        }

        const body = node.statements;

        let declarations = [];
        let emitsAndReturns = [];
        let assertRequireStatements = [];
        let stateChanges = [];
        let nonStateChanges = [];
        
        // Separa le state changes dalle non-state changes
        body.forEach(statement => {
            if (!statement) {
                return;
            }

            if (statement.type === "ReturnStatement" || statement.type === "EmitStatement") {
                emitsAndReturns.push(statement)
                return;
            }
            
            if (statement.type === 'VariableDeclarationStatement' &&
                statement.initialValue
            ) {
                if(isNonStateChange(statement.initialValue) && !structContractsDefinitions.includes(statement.initialValue.expression.name)){
                    nonStateChanges.push(statement)
                } else {
                    declarations.push(statement);
                }
                
                return;
            }
    
            if (statement.type === "ExpressionStatement" &&
                statement.expression.type === "FunctionCall" &&
                statement.expression.expression.type === "Identifier" &&
                events.includes(statement.expression.expression.name)
            ) {
                stateChanges.push(statement);
                return;
            }
    
            if (isNonStateChange(statement)) {
                nonStateChanges.push(statement);
            } else {
                if(statement.type === 'ExpressionStatement' &&
                    statement.expression &&
                    statement.expression.expression &&
                    (statement.expression.expression.name === 'assert' || statement.expression.expression.name === 'require'))
                {
                    assertRequireStatements.push(statement);
                } else {
                    stateChanges.push(statement);
                }
                
            }

        });

        

        if (stateChanges.length > 0 && nonStateChanges.length > 0) {
            const start = body[0].range[0];
            const end = body[body.length - 1].range[1] + 1;
            const startLine = body[0].loc.start.line;
            const endLine = body[body.length - 1].loc.end.line;
            const original = source.slice(start, end);

            const combinedStatements = [
                ...declarations,
                ...assertRequireStatements,
                ...nonStateChanges,
                //"if( ! (msg.sender.call() ) ){throw;}",
                ...stateChanges,
                ...emitsAndReturns
            ];

            let replacement = combinedStatements.map(statement => {
                if (typeof statement === "string") {
                    return statement; // Restituisce la chiamata "msg.sender.call();"
                }
                return source.slice(statement.range[0], statement.range[1] + 1);
            }).join("\n");

            // Sostituisci i doppi ";" con un singolo
            replacement = replacement.replace(/;{2,}/g, ';');

            if (replacement !== original) {
                mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
            }
        }
        
    }

    return mutations;
};

module.exports = ROSOperator;
