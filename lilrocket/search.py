import datetime
import os
import re
import warnings
from lilrocket.exceptions import MissingDependency, WhooshError
try:
    from whoosh import store
    from whoosh.fields import Schema, ID, STORED, TEXT, KEYWORD
    import whoosh.index as index
    from whoosh.qparser import QueryParser
    from whoosh.spelling import SpellChecker
except ImportError:
    raise MissingDependency("The 'whoosh' backend requires the installation of 'Whoosh'. Please refer to the documentation.")

# Word reserved by Whoosh for special use.
RESERVED_WORDS = (
    'AND',
    'NOT',
    'OR',
    'TO',
)

# Characters reserved by Whoosh for special use.
# The '\\' must come first, so as not to overwrite the other slash replacements.
RESERVED_CHARACTERS = (
    '\\', '+', '-', '&&', '||', '!', '(', ')', '{', '}',
    '[', ']', '^', '"', '~', '*', '?', ':', '.',
)

DATETIME_REGEX = re.compile('^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})T(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})(\.\d{3,6}Z?)?$')


# DRL_FIXME: Added thread locking to everything.
class WhooshSearch(object):
    def __init__(self, index_filepath, schema_filepath, content_field_name,
                 include_spelling=False):
        self.index_filepath = index_filepath
        self.schema_filepath = schema_filepath
        self.content_field_name = content_field_name
        self.include_spelling = include_spelling
        self.setup()
    
    def setup(self):
        new_index = False
        
        # Make sure the index is there.
        if not os.path.exists(self.index_filepath):
            os.makedirs(self.index_filepath)
            new_index = True
        
        # DRL_FIXME: Need to handle schema.
        #            * Check the filepath (Exists? Readable?)
        #            * Add it to the PYTHONPATH?
        #            * Try to import the schema (bail out if busted).
        
        self.storage = store.FileStorage(self.index_filepath)
        self.parser = QueryParser(content_field_name, schema=self.schema)
        
        if new_index is True:
            self.index = index.create_in(index_filepath, self.schema)
        else:
            try:
                self.index = index.Index(self.storage, schema=self.schema)
            except index.EmptyIndexError:
                self.index = index.create_in(index_filepath, self.schema)
    
    def update(self, documents, commit=True):
        writer = self.index.writer()
        
        for doc in documents:
            writer.update_document(**doc)
        
        if commit is True:
            writer.commit()
        
        # If spelling support is desired, add to the dictionary.
        if self.include_spelling is True:
            sp = SpellChecker(self.storage)
            sp.add_field(self.index, self.content_field_name)
    
    def remove(self, whoosh_id, commit=True):
        self.index.delete_by_query(q=self.parser.parse('id:"%s"' % whoosh_id))
        
        if commit is True:
            self.index.commit()
    
    def clear(self, query='', commit=True):
        if not query:
            self.delete_index()
        else:
            self.index.delete_by_query(q=self.parser.parse(query))
        
        if commit is True:
            self.index.commit()
    
    def delete_index(self):
        # Per the Whoosh mailing list, if wiping out everything from the index,
        # it's much more efficient to simply delete the index files.
        if os.path.exists(self.index_filepath):
            index_files = os.listdir(self.index_filepath)
        
            for index_file in index_files:
                os.remove(os.path.join(self.index_filepath, index_file))
        
            os.removedirs(self.index_filepath)
        
        # Recreate everything.
        self.setup()
    
    def optimize(self):
        self.index.optimize()
    
    def search(self, query_string, sort_by=None, start_offset=0, end_offset=None,
               fields='', highlight=False, facets=None, date_facets=None, query_facets=None,
               narrow_queries=None, **kwargs):
        # A zero length query should return no results.
        if len(query_string) == 0:
            return self._process_results([])
        
        # A one-character query (non-wildcard) gets nabbed by a stopwords
        # filter and should yield zero results.
        if len(query_string) <= 1 and query_string != '*':
            return self._process_results([])
        
        reverse = False
        
        if sort_by is not None:
            # Determine if we need to reverse the results and if Whoosh can
            # handle what it's being asked to sort by. Reversing is an
            # all-or-nothing action, unfortunately.
            sort_by_list = []
            reverse_counter = 0
            
            for order_by in sort_by:
                if order_by.startswith('-'):
                    reverse_counter += 1
            
            if len(sort_by) > 1 and reverse_counter > 1:
                raise WhooshError("Whoosh does not handle more than one field and any field being ordered in reverse.")
            
            for order_by in sort_by:
                if order_by.startswith('-'):
                    sort_by_list.append(order_by[1:])
                    
                    if len(sort_by_list) == 1:
                        # Odd ordering but correct.
                        reverse = False
                else:
                    sort_by_list.append(order_by)
                    
                    if len(sort_by_list) == 1:
                        # Odd ordering but correct.
                        reverse = True
                
            sort_by = sort_by_list[0]
        
        if facets is not None:
            warnings.warn("Whoosh does not handle faceting.", Warning, stacklevel=2)
        
        if date_facets is not None:
            warnings.warn("Whoosh does not handle date faceting.", Warning, stacklevel=2)
        
        if query_facets is not None:
            warnings.warn("Whoosh does not handle query faceting.", Warning, stacklevel=2)
        
        narrowed_results = None
        
        if narrow_queries is not None:
            # Potentially expensive? I don't see another way to do it in Whoosh...
            narrow_searcher = self.index.searcher()
            
            for nq in narrow_queries:
                recent_narrowed_results = narrow_searcher.search(self.parser.parse(nq))
                
                if narrowed_results:
                    narrowed_results.filter(recent_narrowed_results)
                else:
                   narrowed_results = recent_narrowed_results
        
        if self.index.doc_count:
            searcher = self.index.searcher()
            parsed_query = self.parser.parse(query_string)
            
            # In the event of an invalid/stopworded query, recover gracefully.
            if parsed_query is None:
                return {
                    'results': [],
                    'hits': 0,
                }
            
            # DRL_TODO: Ignoring offsets for now, as slicing caused issues with pagination.
            raw_results = searcher.search(parsed_query, sortedby=sort_by, reverse=reverse)
            
            # Handle the case where the results have been narrowed.
            if narrowed_results:
                raw_results.filter(narrowed_results)
        else:
            # Nothing in the index. Fake no results.
            raw_results = []
        
        return self._process_results(raw_results, highlight=highlight, query_string=query_string)
    
    def _process_results(self, raw_results, highlight=False, query_string=''):
        results = {
            'hits': 0
            'docs': [],
            'facets': {},
            'highlighted': {},
            'spelling_suggestion': None,
        }
        
        for doc_offset, raw_result in enumerate(raw_results):
            raw_result = dict(raw_result)
            final_result = {}
            
            for key, value in raw_result.items():
                final_result[str(key)] = self._to_python(value)
            
            if highlight:
                from whoosh import analysis
                from whoosh.highlight import highlight, ContextFragmenter, UppercaseFormatter
                sa = analysis.StemmingAnalyzer()
                terms = [term.replace('*', '') for term in query_string.split()]
                
                # DRL_FIXME: Highlighting doesn't seem to work properly in testing.
                results['highlighted'][self.content_field_name] = [highlight(additional_fields.get(self.content_field_name), terms, sa, ContextFragmenter(terms), UppercaseFormatter())]
            
            # Requires Whoosh 0.1.20+.
            if hasattr(raw_results, 'score'):
                final_result['score'] = raw_results.score(doc_offset)
            else:
                final_result['score'] = 0
            
            results['docs'].append(final_result)
        
        if self.include_spelling:
            results['spelling_suggestion'] = self.create_spelling_suggestion(query_string)
        
        # DRL_FIXME: This needs to be corrected.
        results['hits'] = len(results['docs'])
        return results
    
    def create_spelling_suggestion(self, query_string):
        spelling_suggestion = None
        sp = SpellChecker(self.storage)
        cleaned_query = query_string
        
        if not query_string:
            return spelling_suggestion
        
        # Clean the string.
        for rev_word in RESERVED_WORDS:
            cleaned_query = cleaned_query.replace(rev_word, '')
        
        for rev_char in RESERVED_CHARACTERS:
            cleaned_query = cleaned_query.replace(rev_char, '')
        
        # Break it down.
        query_words = cleaned_query.split()
        suggested_words = []
        
        for word in query_words:
            suggestions = sp.suggest(word, number=1)
            
            if len(suggestions) > 0:
                suggested_words.append(suggestions[0])
        
        spelling_suggestion = ' '.join(suggested_words)
        return spelling_suggestion
    
    def _from_python(self, value):
        """
        Converts Python values to a string for Whoosh.
        
        Code courtesy of pysolr.
        """
        if isinstance(value, datetime.datetime):
            value = force_unicode('%s' % value.isoformat())
        elif isinstance(value, datetime.date):
            value = force_unicode('%sT00:00:00' % value.isoformat())
        elif isinstance(value, bool):
            if value:
                value = u'true'
            else:
                value = u'false'
        else:
            value = force_unicode(value)
        return value
    
    def _to_python(self, value):
        """
        Converts values from Whoosh to native Python values.
        
        A port of the same method in pysolr, as they deal with data the same way.
        """
        if value == 'true':
            return True
        elif value == 'false':
            return False
        
        possible_datetime = DATETIME_REGEX.search(value)
        
        if possible_datetime:
            date_values = possible_datetime.groupdict()
            
            for dk, dv in date_values.items():
                date_values[dk] = int(dv)
            
            return datetime.datetime(date_values['year'], date_values['month'], date_values['day'], date_values['hour'], date_values['minute'], date_values['second'])
        
        try:
            # This is slightly gross but it's hard to tell otherwise what the
            # string's original type might have been. Be careful who you trust.
            converted_value = eval(value)
            
            # Try to handle most built-in types.
            if isinstance(converted_value, (list, tuple, set, dict, int, float, long, complex)):
                return converted_value
        except:
            # If it fails (SyntaxError or its ilk) or we don't trust it,
            # continue on.
            pass
        
        return value
