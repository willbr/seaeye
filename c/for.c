#include <stdio.h>
#include <string.h>
#include <assert.h>
#include <stdbool.h>

// watchexec --clear --restart --exts c
/*
for word in 'one two three'.split(' ')
    print word
    */

typedef struct {
	char   *haystack;
	char   *sep;
	size_t  sep_length;
	char   *next;
	int     finished;
} String_Iter;


void
next(String_Iter *ctx, char **word, int *len) {
	char *sep = NULL;
	if (ctx->next == NULL) {
		ctx->next = ctx->haystack;
	}

	*word = ctx->next;

	sep = strstr(ctx->next, ctx->sep);
	if (sep == NULL) {
		*len = strlen(ctx->next);
		ctx->next += *len;
		ctx->finished = true;
	} else {
		*len = sep - *word;
		ctx->next += *len + ctx->sep_length;
	}
}


int
main(int argc, char **argv) {
	char *word = NULL;
	int word_length = 0;
	char haystack[] = "one two three";

	String_Iter context = {
		.haystack = haystack,
		.sep = " ",
		.sep_length = strlen(" "),
	};

	while (!context.finished) {
		next(&context, &word, &word_length);
		printf("\"%.*s\"\n", word_length, word);
		if (context.finished) {
			break;
		}

	}
	return 0;
}

