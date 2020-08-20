#!/mnt/lustre/software/linuxbrew/colsa/bin/python3
import sys

def annotate_with_blastp(blast_results):
    """ blastp against custom mito protein reference, outfmt 6    """
    contig_lookup = {}
    for line in open(blast_results):
        # 'qaccver saccver pident length mismatch gapopen qstart qend sstart send evalue bitscore'
        elements = line.rstrip().split('\t')
        contig = elements[0]; hit = elements[1]
        p_id = elements[2]; match_length = elements[3]
        if contig not in contig_lookup.keys():
            contig_lookup[contig] = True
    return contig_lookup

def annotate_with_nt_blast(nt_blast_results):
    contig_lookup = {} # contig: [mito_count, nuclear_count]
    first_hit_lookup = {} # contig: [best, hit, results]
    for line in open(nt_blast_results):
        elements = line.rstrip().split('\t')
        sequence_id = elements[0]; tax_code = elements[2]
        percent_id = elements[3]; length_hit = elements[4]
        length_query = elements[1]; full_hit = elements[-1]
        if sequence_id not in contig_lookup.keys():
            contig_lookup[sequence_id] = [0,0]
            first_hit_lookup[sequence_id] = elements
        if sum(contig_lookup[sequence_id]) < 6:
            if "mitochon" in full_hit.lower():
                contig_lookup[sequence_id][0] += 1
            else:
                contig_lookup[sequence_id][1] += 1
    return contig_lookup, first_hit_lookup

def populate_taxonomy_w_blobtools(input_taxonomy, tax_level_to_group):
    ''' parse a taxonomy file for rep taxon, GC and full taxonomy'''
    taxonomy_dictionary = {} #contig_name: [rep_taxon, GC, [full_taxonomy]]
    list_of_unique_taxa = []
    group_bacteria = True
    for b in open(input_taxonomy):
        if b[0] != '#':
            elements = b.rstrip().split('\t')
            node = elements[0].lstrip().rstrip()
            #kmer_coverage = elements[1]
            gc = elements[2]
            #coverage = elements[4]
            #taxonomy = [x.lstrip().rstrip() for x in [elements[6],elements[9],elements[12], elements[15],elements[18],elements[21]]]
            taxonomy = [x.lstrip().rstrip() for x in [elements[5],elements[8],elements[11], elements[14],elements[17],elements[20]]]
            #tax_levels = ['kingdom', 'phylum', 'order', 'family', 'genus', 'species']
            #taxonomy = [x.lstrip().rstrip() for x in elements[4:]]
            rep_taxon = taxonomy[tax_level_to_group]
            if group_bacteria:
                if taxonomy[0] == 'Bacteria' or 'bacteria' in ','.join(taxonomy) or taxonomy[0] == "Archaea":
                    rep_taxon = 'Bacteria'
            if rep_taxon not in list_of_unique_taxa:
                list_of_unique_taxa.append(rep_taxon)
            taxonomy_dictionary[node] = [rep_taxon, gc, taxonomy]
    list_of_unique_taxa = sorted(list_of_unique_taxa)
    return taxonomy_dictionary, list_of_unique_taxa

def populate_coverages(input_table):
    """ Given a table with coverages, populate a per contig table"""
    contig_coverages = {} # contig: coverage
    header = True
    for line in open(input_table):
        if header:
           header = False
        else:
            contig, length, coverage = line.rstrip().split('\t')
            contig_coverages[contig] = [coverage, length]
    return contig_coverages

def fold_enrichment(number1, number2):
    replace_value = 0.1
    if float(number1) >= float(number2): # positive value
        if float(number2) == 0:
            number2 = replace_value
        enrichment = float(number1)/float(number2)
    else: # negative value
        if float(number1) == 0:
            number1 = replace_value
        enrichment = float(number2)/float(number1)
        enrichment = 0 - enrichment # convert to negative
    return enrichment


def complexity(file):
    complex_dict = {}
    for line in open(file):
        elements = line.rstrip().split('\t')
        complex_dict[elements[0]] = elements[1:]
    return complex_dict

working_dir = "/mnt/lustre/hcgs/joseph7e/GOMRI/Project_Folders/Metagenomics_and_Metabarcoding/Mitochondrial_Enrichment/May_Kappa_Subsets/Sample_P1C09/"
fasta_file = sys.argv[1]#working_dir + "P1C09.fasta"

# Parse coverage tables
mito_coverage_file  = sys.argv[2]#working_dir + "bwa_mapping_bwaP1C09_enriched/concoct_inputtable.tsv"
coverage_file = sys.argv[3]#working_dir + "bwa_mapping_bwaP1C09/concoct_inputtable.tsv"
mito_coverage_lookup = populate_coverages(mito_coverage_file)
coverage_lookup = populate_coverages(coverage_file)

# gather taxonomy data
blobtools_taxonomy = sys.argv[4]#working_dir + "P1C09.taxonomy.P1C09.blobDB.table.txt"
taxonomy_dictionary, unique_taxa = populate_taxonomy_w_blobtools(blobtools_taxonomy,1)

# annotate mitochondria
nt_blast_results = sys.argv[5]#working_dir + "Sample_P1_C09.fasta.vs.nt.cul5.1e5.megablast.out"
blastp_results = ""#sys.argv[6]#working_dir + "parsed_blastp.tsv"
mito_lookup_nt, top_hit_lookup = annotate_with_nt_blast(nt_blast_results)
mito_lookup_blastp = {}#annotate_with_blastp(blastp_results)
mito_lookup_prokka = ''
prokka_results = working_dir + ""


# complexity data
# complexity_file = sys.argv[6]
# complexity_lookup = complexity(complexity_file)

print ("Contig\tLength\tFold-enrichment\tOrigin\tGC\tRep-taxon\tMito-coverage\tCoverage\tMito_Cov_weighted\tCov_weighted\tTaxonomy\tcounts\tTop_BLAST")#\t"+'\t'.join(complexity_lookup['seq']))
for contig, data in taxonomy_dictionary.items():
    mito_coverage,length = mito_coverage_lookup[contig]
    coverage,length = coverage_lookup[contig]
    rep_taxon, gc, taxonomy = taxonomy_dictionary[contig]
    try:
        mitochondrial_hits,nuclear_hits = mito_lookup_nt[contig]
        if mitochondrial_hits >= nuclear_hits:
            origin = "Mitochondrial"
        else:
            origin = "Nuclear"
    except:
        origin = "UNKNOWN"
        mitochondrial_hits,nuclear_hits = 0,0
    if contig in mito_lookup_blastp.keys():
        origin += ":blastp_mitochondria"
    else:
        origin += ":blastp_none"
    mito_weighted = int(length) * float(mito_coverage)
    weighted = int(length) * float(coverage)
    enrichment = fold_enrichment(mito_coverage, coverage)
    try:
        blast_hit = ':'.join(top_hit_lookup[contig])
    except:
        blast_hit = 'NO-HIT'
    # try:
    #     complexity = complexity_lookup[contig]
    # except:
    #     complexity = complexity_lookup['seq']
    data = [contig, str(length), str(enrichment), origin,str(gc), rep_taxon, str(mito_coverage), str(coverage), str(mito_weighted),str(weighted),';'.join(taxonomy), str(mitochondrial_hits) + ':' + str(nuclear_hits), blast_hit]#, '\t'.join(complexity)]
    print ('\t'.join(data))