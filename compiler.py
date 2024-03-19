import parse
import asm

ast = parse.parse_file('gameboy.ci')


def compile_statement(statement):
    cmd, args, block, comments = statement
    # print(statement)

    fn = asm.words.get(cmd, None)
    assert fn is not None
    fn(args, block, comments)

def main():
    for statement in ast:
        compile_statement(statement)
    asm.resolve()
    asm.calc_header_checksum()
    asm.calc_global_checksum()
    asm.write_rom('out.gb')

if __name__ == '__main__':
    main()

