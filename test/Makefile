CXX      ?= g++
CXXFLAGS ?= -std=c++17 -O2 -Wall -Wextra \
            -I../phase_c_upgraded/include -I/usr/include/eigen3

PHASE_C_DIR ?= ../phase_c_upgraded

.PHONY: all verify figure manuscript clean

all: verify figure manuscript

verify: phase_d_verify
	./phase_d_verify
	@echo "Wrote phase_d_gap_scan.csv"

phase_d_verify: phase_d_verify.cpp
	$(CXX) $(CXXFLAGS) -o $@ $<

figure: phase_d_fig1.pdf

phase_d_fig1.pdf: phase_d_gap_scan.csv make_fig1.py
	python3 make_fig1.py

phase_d_gap_scan.csv: phase_d_verify
	./phase_d_verify

manuscript: phase_d_manuscript.pdf

phase_d_manuscript.pdf: phase_d_manuscript.tex phase_d_fig1.pdf
	pdflatex -interaction=nonstopmode phase_d_manuscript.tex > /dev/null
	pdflatex -interaction=nonstopmode phase_d_manuscript.tex > /dev/null
	@echo "Wrote phase_d_manuscript.pdf"

clean:
	rm -f phase_d_verify phase_d_gap_scan.csv
	rm -f phase_d_fig1.pdf phase_d_fig1.png
	rm -f phase_d_manuscript.pdf phase_d_manuscript.log
	rm -f phase_d_manuscript.aux phase_d_manuscript.out
	rm -f page-*.png
