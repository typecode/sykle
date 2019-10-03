def kebab_arg_to_snake_case(arg):
    # trim the --
    arg = arg[2:]

    return '_'.join(x for x in arg.split('-'))
