import csv
import sys


def read_mealy(mealy_filename):
    transitions = {}
    input_symbols = []

    with open(mealy_filename, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file, delimiter=';')
        headers = next(reader)
        states = headers[1:]

        for row in reader:
            input_symbol = row[0]
            input_symbols.append(input_symbol)
            transitions[input_symbol] = {}

            for i, value in enumerate(row[1:], start=0):
                state = states[i]
                output, next_state = value.split('/')
                transitions[input_symbol][state] = (output, next_state)

    return transitions, states, input_symbols


def mealy_to_moore(mealy_filename, output_filename):
    transitions, states, input_symbols = read_mealy(mealy_filename)
    transitions, states = remove_unreachable_states_mealy(transitions, states, input_symbols)
    moore_transitions = {}
    old_to_new = extract_unique_sorted_tuples(transitions, states[0])

    for input_symbol in input_symbols:
        moore_transitions[input_symbol] = {}
        for old, new in old_to_new.items():
            state, output = old
            tuple = transitions[input_symbol][state]
            new_state = old_to_new[tuple]
            moore_transitions[input_symbol][new] = new_state

    outputs = {v: k[1] for k, v in old_to_new.items()}

    states = list(outputs.keys())
    print_moore(output_filename, moore_transitions, outputs, states, input_symbols)
    return moore_transitions, outputs, states, input_symbols


def moore_to_mealy(moore_filename, output_filename):
    transitions, outputs, states, input_symbols = read_moore(moore_filename)
    transitions, states = remove_unreachable_states_moore(transitions, states, input_symbols)
    mealy_transitions = {}

    for input_symbol in input_symbols:
        mealy_transitions[input_symbol] = {}
        for state in states:
            mealy_transitions[input_symbol][state] = (
            transitions[input_symbol][state], outputs[transitions[input_symbol][state]])
    print_mealy(output_filename, mealy_transitions, states, input_symbols)
    return mealy_transitions, states, input_symbols


def minimize_moore(moore_filename, output_filename):
    transitions, outputs, states, input_symbols = read_moore(moore_filename)
    transitions, states = remove_unreachable_states_moore(transitions, states, input_symbols)

    groups = {}
    for state, output in outputs.items():
        if output not in groups:
            groups[output] = []
        groups[output].append(state)
    groups_map = {}
    for number, group in enumerate(groups.values(), start=1):
        for member in group:
            groups_map[member] = f'a{number}'

    is_changed = True
    while is_changed:
        is_changed = False
        new_groups_map = {}
        state_to_transitions = {}

        for state in states:
            for input_symbol in input_symbols:
                transition = transitions[input_symbol][state]
                to_group = groups_map[transition]
                if state not in state_to_transitions.keys():
                    state_to_transitions[state] = []
                state_to_transitions[state].append(to_group)

        transitions_to_group = {}
        for state, ts in state_to_transitions.items():
            group = groups_map[state]

            transitions_key = tuple(ts)

            unique_key = (transitions_key, group)

            if unique_key in transitions_to_group:
                existing_group = transitions_to_group[unique_key]
                new_groups_map[state] = existing_group
            else:
                new_group_name = f'a{len(transitions_to_group) + 1}'
                transitions_to_group[unique_key] = new_group_name
                new_groups_map[state] = new_group_name

        groups_map = new_groups_map
        if len(set(groups_map.values())) != len(set(new_groups_map.values())):
            is_changed = True
        else:
            transitions, outputs = build_minimized_moore(transitions, outputs, new_groups_map)

    print_moore(output_filename, transitions, outputs, list(outputs.keys()), input_symbols)


def build_minimized_moore(transitions, outputs, new_groups_map):
    new_transitions = {}
    new_outputs = {}

    for z, state_map in transitions.items():
        new_state_map = {}
        for state, next_state in state_map.items():
            new_state = new_groups_map[state]
            new_next_state = new_groups_map[next_state]

            if new_state not in new_state_map:
                new_state_map[new_state] = new_next_state

        new_transitions[z] = new_state_map

    for state, output in outputs.items():
        new_outputs[new_groups_map[state]] = output

    return new_transitions, new_outputs


def minimize_mealy(mealy_filename, output_filename):
    transitions, states, input_symbols = read_mealy(mealy_filename)
    transitions, states = remove_unreachable_states_mealy(transitions, states, input_symbols)

    state_outputs = {}
    for state_map in transitions.values():
        for state, (next_state, output) in state_map.items():
            if state not in state_outputs:
                state_outputs[state] = []
            state_outputs[state].append(output)
    groups = {}
    for state, outputs in state_outputs.items():
        outputs_key = tuple(outputs)
        if outputs_key not in groups:
            groups[outputs_key] = []
        groups[outputs_key].append(state)
    groups_map = {}
    for number, group in enumerate(groups.values(), start=1):
        for member in group:
            groups_map[member] = f'a{number}'

    is_changed = True
    while is_changed:
        is_changed = False
        new_groups_map = {}
        state_to_transitions = {}

        for state in states:
            for input_symbol in input_symbols:
                transition = transitions[input_symbol][state][0]
                to_group = groups_map[transition]
                if state not in state_to_transitions.keys():
                    state_to_transitions[state] = []
                state_to_transitions[state].append(to_group)

        transitions_to_group = {}
        for state, ts in state_to_transitions.items():
            group = groups_map[state]

            transitions_key = tuple(ts)

            unique_key = (transitions_key, group)

            if unique_key in transitions_to_group:
                existing_group = transitions_to_group[unique_key]
                new_groups_map[state] = existing_group
            else:
                new_group_name = f'a{len(transitions_to_group) + 1}'
                transitions_to_group[unique_key] = new_group_name
                new_groups_map[state] = new_group_name

        groups_map = new_groups_map
        if len(set(groups_map.values())) != len(set(new_groups_map.values())):
            is_changed = True
        else:
            transitions, states = build_minimized_mealy(transitions, new_groups_map)

    print_mealy(output_filename, transitions, states, input_symbols)


def build_minimized_mealy(transitions, new_groups_map):
    new_transitions = {}

    for z, state_map in transitions.items():
        new_state_map = {}
        for state, (next_state, output) in state_map.items():
            new_state = new_groups_map[state]
            new_next_state = new_groups_map[next_state]

            if new_state not in new_state_map:
                new_state_map[new_state] = (new_next_state, output)

        new_transitions[z] = new_state_map

    return new_transitions, list(set(new_groups_map.values()))


def remove_unreachable_states_mealy(transitions, states, input_symbols):
    reachable_states = set()
    states_to_visit = {states[0]}

    while states_to_visit:
        current_state = states_to_visit.pop()
        reachable_states.add(current_state)

        for input_symbol in input_symbols:
            if current_state in transitions[input_symbol]:
                next_state, _ = transitions[input_symbol][current_state]
                if next_state not in reachable_states:
                    states_to_visit.add(next_state)

    for input_symbol in input_symbols:
        for state in list(transitions[input_symbol].keys()):
            if state not in reachable_states:
                del transitions[input_symbol][state]

    states = [state for state in states if state in reachable_states]

    return transitions, states


def remove_unreachable_states_moore(transitions, states, input_symbols):
    reachable_states = set()
    states_to_visit = {states[0]}

    while states_to_visit:
        current_state = states_to_visit.pop()
        reachable_states.add(current_state)

        for input_symbol in input_symbols:
            if current_state in transitions[input_symbol]:
                next_state = transitions[input_symbol][current_state]
                if next_state not in reachable_states:
                    states_to_visit.add(next_state)

    for input_symbol in input_symbols:
        for state in list(transitions[input_symbol].keys()):
            if state not in reachable_states:
                del transitions[input_symbol][state]

    states = [state for state in states if state in reachable_states]
    return transitions, states


def extract_unique_sorted_tuples(data, start):
    unique_tuples = set()
    for input_symbol, state_transitions in data.items():
        for state, (next_state, output) in state_transitions.items():
            unique_tuples.add((next_state, output))

    if not any(start == item[0] for item in unique_tuples):
        unique_tuples.add((start, ""))
    sorted_unique_tuples = sorted(unique_tuples)
    old_to_new = {}

    for idx, state_tuple in enumerate(sorted_unique_tuples):
        new_name = f'q{idx}'
        old_to_new[state_tuple] = new_name

    return old_to_new


def read_moore(moore_filename):
    transitions = {}
    states = []
    input_symbols = []
    outputs = {}

    with open(moore_filename, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file, delimiter=';')
        headers = next(reader)
        output_symbols = headers[1:]
        states_row = next(reader)
        states = states_row[1:]

        for state, output_symbol in zip(states, output_symbols):
            outputs[state] = output_symbol

        for row in reader:
            input_symbol = row[0]
            input_symbols.append(input_symbol)
            transitions[input_symbol] = {}
            for i, state in enumerate(states):
                next_state = row[i + 1]
                transitions[input_symbol][state] = next_state

    return transitions, outputs, states, input_symbols


def print_mealy(output_filename, transitions, states, input_symbols):
    with open(output_filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file, delimiter=';')
        header = [''] + states
        writer.writerow(header)

        for input_symbol in input_symbols:
            row = [input_symbol]
            for state in states:
                output, next_state = transitions[input_symbol].get(state, ('', ''))
                row.append(f'{output}/{next_state}')
            writer.writerow(row)


def print_moore(output_filename, transitions, outputs, states, input_symbols):
    with open(output_filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file, delimiter=';')
        header1 = [''] + list(outputs.values())
        writer.writerow(header1)
        header2 = [''] + states
        writer.writerow(header2)

        for input_symbol in input_symbols:
            row = [input_symbol]
            for state in states:
                next_state = transitions[input_symbol].get(state, '')
                row.append(next_state)
            writer.writerow(row)


def main():
    if len(sys.argv) != 4:
        print("Использование:")
        print("Для минимизации Mealy:")
        print("    program mealy mealy.csv output.csv")
        print("Для минимизации Moore:")
        print("    program moore moore.csv output.csv.csv")
        sys.exit(1)

    command = sys.argv[1]
    input_file = sys.argv[2]
    output_file = sys.argv[3]

    if command == "mealy":
        minimize_mealy(input_file, output_file)
    elif command == "moore":
        minimize_moore(input_file, output_file)
    else:
        print(f"Неизвестная команда: {command}")
        print("Допустимые команды: 'mealy' или 'moore'")
        sys.exit(1)


if __name__ == "__main__":
    main()
