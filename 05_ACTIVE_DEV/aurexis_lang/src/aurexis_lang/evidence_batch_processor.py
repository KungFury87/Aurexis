"""
Evidence Batch Processing System

Processes captured evidence batches through the full Aurexis pipeline to generate
real-world performance metrics and training data.
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime
from .real_evidence_capture import EvidenceCapture
from .perception_dataset_prep import rank_row_usefulness, build_dataset_manifest
from .evaluation_loop_scaffold import evaluate_rows, summarize_by_provenance
from .gate3_evidence_loop import evaluate_gate3_evidence_loop
from .gate3_batch_comparison import compare_authored_summary_to_batch
from .gate3_batch_reporting import build_gate3_batch_report_surface
from .gate3_completion_audit import audit_gate3_completion
from .gate3_earned_promotion import promote_gate3_earned_candidate
from .gate3_gate_completion_audit import audit_gate3_gate_completion
from .gate3_saved_run_audit import build_gate3_gate_completion_audit_from_project_root
from .gate3_global_completion import build_gate3_global_completion_report
from .gate3_saved_seed import build_gate3_canonical_saved_seed, GATE_3_CANONICAL_SAVED_SEED_RULES_VERSION
from .gate3_packaged_default_state import (
    clear_gate3_saved_outputs,
    build_gate3_final_completion_report,
    GATE_3_PACKAGED_DEFAULT_STATE_RULES_VERSION,
)
from .gate3_default_pipeline import (
    build_gate3_default_pipeline_stamp,
    GATE_3_DEFAULT_PIPELINE_RULES_VERSION,
)
from .gate3_release_pipeline import (
    build_gate3_root_package_completion_stamp,
    GATE_3_RELEASE_PIPELINE_RULES_VERSION,
)
from .gate4_mobile_demo_kickoff import (
    build_gate4_narrow_mobile_demo_report,
    GATE_4_NARROW_MOBILE_DEMO_RULES_VERSION,
)
from .gate3_multi_route_completion import (
    build_gate3_saved_route_package,
    build_validation_cycle_results_from_route_package,
    build_complete_cycle_results_from_route_package,
)


class EvidenceBatchProcessor:
    """Processes evidence batches through the full Aurexis pipeline"""
    
    def __init__(self, evidence_dir: str = "evidence_batches"):
        self.evidence_dir = Path(evidence_dir)
        self.results_dir = Path("processing_results")
        self.results_dir.mkdir(exist_ok=True)

    def _feature_vector_from_evidence(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        """Build a stable feature vector from an evidence record for downstream scoring."""
        confidence = float(evidence.get('confidence', {}).get('overall', 0.0) or 0.0)
        primitive_count = int(evidence.get('cv_extraction', {}).get('primitive_count', 0) or 0)
        segment_count = int(evidence.get('segmentation_extraction', {}).get('segments_count', 0) or 0)
        return {
            'average_candidate_confidence': confidence,
            'stable_across_thresholds': confidence >= 0.7 and primitive_count > 0,
            'role_disagreement': False,
            'unique_role_count': max(1, min(primitive_count, segment_count, 4)),
        }
    
    def list_available_batches(self) -> List[str]:
        """List all available evidence batches"""
        if not self.evidence_dir.exists():
            return []
        
        batches = []
        for item in self.evidence_dir.iterdir():
            if item.is_dir() and (item / "evidence.json").exists():
                batches.append(item.name)
        
        return sorted(batches)
    
    def load_batch(self, batch_name: str) -> List[Dict[str, Any]]:
        """Load evidence data from a batch"""
        batch_file = self.evidence_dir / batch_name / "evidence.json"
        
        if not batch_file.exists():
            raise FileNotFoundError(f"Batch {batch_name} not found")
        
        with open(batch_file, 'r') as f:
            return json.load(f)
    
    def load_batch_summary(self, batch_name: str) -> Dict[str, Any]:
        """Load batch summary statistics"""
        summary_file = self.evidence_dir / batch_name / "summary.json"
        
        if not summary_file.exists():
            return {}
        
        with open(summary_file, 'r') as f:
            return json.load(f)
    
    def analyze_batch_quality(self, batch_name: str) -> Dict[str, Any]:
        """Analyze quality metrics for a batch"""
        evidence_data = self.load_batch(batch_name)
        summary = self.load_batch_summary(batch_name)
        
        quality_analysis = {
            'batch_name': batch_name,
            'total_records': len(evidence_data),
            'confidence_distribution': self._analyze_confidence_distribution(evidence_data),
            'primitive_analysis': self._analyze_primitive_patterns(evidence_data),
            'temporal_analysis': self._analyze_temporal_patterns(evidence_data),
            'processing_gaps': self._identify_processing_gaps(evidence_data),
            'quality_score': self._calculate_overall_quality(evidence_data, summary)
        }
        
        return quality_analysis
    
    def _analyze_confidence_distribution(self, evidence_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze confidence score distribution"""
        confidence_scores = []
        
        for evidence in evidence_data:
            if 'confidence' in evidence and 'overall' in evidence['confidence']:
                confidence_scores.append(evidence['confidence']['overall'])
        
        if not confidence_scores:
            return {'error': 'No confidence scores found'}
        
        scores = np.array(confidence_scores)
        
        return {
            'mean': float(np.mean(scores)),
            'std': float(np.std(scores)),
            'min': float(np.min(scores)),
            'max': float(np.max(scores)),
            'median': float(np.median(scores)),
            'high_confidence_ratio': float(np.mean(scores > 0.7)),
            'low_confidence_ratio': float(np.mean(scores < 0.3))
        }
    
    def _analyze_primitive_patterns(self, evidence_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze primitive extraction patterns"""
        cv_counts = []
        segment_counts = []
        
        for evidence in evidence_data:
            cv_counts.append(evidence['cv_extraction']['primitive_count'])
            segment_counts.append(evidence['segmentation_extraction']['segments_count'])
        
        cv_counts = np.array(cv_counts)
        segment_counts = np.array(segment_counts)
        
        correlation = 0.0
        if len(cv_counts) > 1 and float(np.std(cv_counts)) > 0.0 and float(np.std(segment_counts)) > 0.0:
            correlation = float(np.corrcoef(cv_counts, segment_counts)[0, 1])

        return {
            'cv_primitives': {
                'mean': float(np.mean(cv_counts)),
                'std': float(np.std(cv_counts)),
                'min': int(np.min(cv_counts)),
                'max': int(np.max(cv_counts))
            },
            'segments': {
                'mean': float(np.mean(segment_counts)),
                'std': float(np.std(segment_counts)),
                'min': int(np.min(segment_counts)),
                'max': int(np.max(segment_counts))
            },
            'correlation': correlation
        }
    
    def _analyze_temporal_patterns(self, evidence_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze temporal patterns in evidence"""
        timestamps = []
        
        for evidence in evidence_data:
            try:
                timestamp = datetime.fromisoformat(evidence['timestamp'].replace('Z', '+00:00'))
                timestamps.append(timestamp)
            except:
                continue
        
        if len(timestamps) < 2:
            return {'error': 'Insufficient temporal data'}
        
        timestamps.sort()
        intervals = [(timestamps[i+1] - timestamps[i]).total_seconds() for i in range(len(timestamps)-1)]
        
        return {
            'duration_seconds': (timestamps[-1] - timestamps[0]).total_seconds(),
            'average_interval': float(np.mean(intervals)),
            'interval_std': float(np.std(intervals)),
            'capture_rate': float(len(timestamps) / (timestamps[-1] - timestamps[0]).total_seconds())
        }
    
    def _identify_processing_gaps(self, evidence_data: List[Dict[str, Any]]) -> List[str]:
        """Identify potential gaps or issues in processing"""
        gaps = []
        
        # Check for missing confidence data
        missing_confidence = sum(1 for e in evidence_data if 'confidence' not in e or 'overall' not in e['confidence'])
        if missing_confidence > 0:
            gaps.append(f"Missing confidence data in {missing_confidence} records")
        
        # Check for zero primitives
        zero_primitives = sum(1 for e in evidence_data if e['cv_extraction']['primitive_count'] == 0)
        if zero_primitives > 0:
            gaps.append(f"Zero primitives in {zero_primitives} records")
        
        # Check for processing errors
        processing_errors = sum(1 for e in evidence_data if 'processing_error' in e)
        if processing_errors > 0:
            gaps.append(f"Processing errors in {processing_errors} records")
        
        return gaps
    
    def _calculate_overall_quality(self, evidence_data: List[Dict[str, Any]], summary: Dict[str, Any]) -> float:
        """Calculate overall quality score for the batch"""
        score = 0.0
        
        # Confidence component (40%)
        if 'confidence' in summary:
            conf_avg = summary['confidence']['average']
            score += 0.4 * conf_avg
        
        # Primitive diversity component (30%)
        if 'cv_primitives' in summary:
            prim_avg = summary['cv_primitives']['average']
            # More primitives is generally better, up to a point
            prim_score = min(prim_avg / 20.0, 1.0)  # Normalize to 0-1
            score += 0.3 * prim_score
        
        # Data volume component (20%)
        record_count = len(evidence_data)
        volume_score = min(record_count / 100.0, 1.0)  # Normalize to 0-1
        score += 0.2 * volume_score
        
        # Completeness component (10%)
        gaps = self._identify_processing_gaps(evidence_data)
        completeness_score = max(0, 1.0 - len(gaps) * 0.1)
        score += 0.1 * completeness_score
        
        return min(score, 1.0)  # Cap at 1.0
    
    def process_batch_to_training_data(self, batch_name: str) -> str:
        """Convert an evidence batch into a ranked training dataset on disk."""
        evidence_data = self.load_batch(batch_name)

        perception_rows = []
        for i, evidence in enumerate(evidence_data):
            try:
                row = self._evidence_to_perception_row(evidence, f"{batch_name}_{i}")
                row['usefulness_score'] = rank_row_usefulness(row)
                perception_rows.append(row)
            except Exception as e:
                print(f"Error converting evidence {i}: {e}")
                continue

        ranked_rows = sorted(
            perception_rows,
            key=lambda row: row.get('usefulness_score', 0.0),
            reverse=True,
        )

        manifest = build_dataset_manifest(ranked_rows)

        training_dir = self.results_dir / f"training_{batch_name}"
        training_dir.mkdir(exist_ok=True)

        manifest_path = training_dir / "manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2, default=str)

        rows_path = training_dir / "rows.json"
        with open(rows_path, 'w') as f:
            json.dump(ranked_rows, f, indent=2, default=str)

        print(f"Created training dataset from {batch_name}: {len(ranked_rows)} rows")
        return str(training_dir)
    
    def _evidence_to_perception_row(self, evidence: Dict[str, Any], row_id: str) -> Dict[str, Any]:
        """Convert evidence record to perception row format with canonical scoring fields."""
        confidence = dict(evidence.get('confidence', {}))
        return {
            'id': row_id,
            'timestamp': evidence.get('timestamp'),
            'source': 'real_capture',
            'provenance': 'observed',
            'status': 'validated' if float(confidence.get('overall', 0.0) or 0.0) >= 0.7 else 'estimated',
            'image_data': {
                'shape': evidence.get('frame_info', {}).get('shape'),
                'size_bytes': evidence.get('frame_info', {}).get('size_bytes')
            },
            'primitives': evidence.get('cv_extraction', {}).get('primitives', []),
            'segments': evidence.get('segmentation_extraction', {}).get('segments_count', 0),
            'confidence': confidence,
            'feature_vector': self._feature_vector_from_evidence(evidence),
            'labels': [],
            'expected_top_role': None,
            'extraction_metadata': {
                'cv_bundle': evidence.get('cv_extraction', {}).get('bundle', {}),
                'segmented_bundle': evidence.get('segmentation_extraction', {}).get('bundle', {})
            }
        }
    
    def run_batch_evaluation(self, batch_name: str) -> Dict[str, Any]:
        """Run evaluation loop on an evidence batch and return a stable summary."""
        evidence_data = self.load_batch(batch_name)

        eval_rows = [
            self._evidence_to_perception_row(evidence, evidence.get('timestamp', f'{batch_name}_{idx}'))
            for idx, evidence in enumerate(evidence_data)
        ]

        eval_results = evaluate_rows(eval_rows)
        provenance_summary = summarize_by_provenance(eval_results)
        row_count = int(eval_results.get('row_count', 0))
        average_score = (
            sum(float(row.get('score', 0.0)) for row in eval_results.get('rows', [])) / row_count
            if row_count else 0.0
        )
        summary = {
            'batch_name': batch_name,
            'row_count': row_count,
            'hit_count': int(eval_results.get('hit_count', 0)),
            'hit_rate': float(eval_results.get('hit_rate', 0.0)),
            'average_score': float(average_score),
            'success_rate': float(eval_results.get('hit_rate', 0.0)),
            'provenance_summary': provenance_summary,
            'gate_3_status': 'IN_PROGRESS',
            'gate_clearance_authority': False,
            'report_scope': 'gate3_batch_evaluation',
            'output_honesty_explicit': True,
        }

        results_file = self.results_dir / f"eval_{batch_name}.json"
        with open(results_file, 'w') as f:
            json.dump({'results': eval_results, 'summary': summary}, f, indent=2, default=str)

        return summary
    

    def build_gate3_batch_comparison(self, batch_name: str, authored_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Build a Gate 3 comparison/audit package from a saved evidence batch and an authored summary."""
        batch_summary = self.load_batch_summary(batch_name)
        source_tiers = []
        if authored_summary:
            source_tiers.append('authored')
        if batch_summary:
            source_tiers.append('real-capture')
        gate3_loop = evaluate_gate3_evidence_loop(
            source_tiers=source_tiers,
            evidence_validated=True,
            multi_frame_consistent=bool(batch_summary.get('batch_size', 0) or 0) > 0,
            output_honesty_explicit=bool(batch_summary.get('output_honesty_explicit', True)),
            gate2_complete=True,
        )
        comparison = compare_authored_summary_to_batch(
            authored_summary=authored_summary,
            batch_summary=batch_summary,
            gate3_evidence_loop=gate3_loop,
        )
        out = {
            'batch_name': batch_name,
            'gate_3_status': 'IN_PROGRESS',
            'gate_clearance_authority': False,
            'evidence_scope': 'authored/real-capture comparison',
            'gate3_evidence_loop': gate3_loop,
            'gate3_batch_comparison': comparison,
        }
        out_file = self.results_dir / f"gate3_compare_{batch_name}.json"
        with open(out_file, 'w') as f:
            json.dump(out, f, indent=2, default=str)
        return out


    def build_gate3_batch_report(self, batch_name: str, authored_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Build a saved Gate 3 report surface from a batch evaluation and comparison package."""
        evaluation_summary = self.run_batch_evaluation(batch_name)
        comparison_package = self.build_gate3_batch_comparison(batch_name, authored_summary)
        earned_candidate = promote_gate3_earned_candidate(comparison_package=comparison_package)
        report_surface = build_gate3_batch_report_surface(
            batch_name=batch_name,
            evaluation_summary=evaluation_summary,
            comparison_package=comparison_package,
            earned_candidate=earned_candidate,
        )
        completion_audit = audit_gate3_completion(batch_report_surface=report_surface)
        out = {
            'batch_name': batch_name,
            'gate_3_status': 'IN_PROGRESS',
            'gate_clearance_authority': False,
            'gate3_batch_report': report_surface,
            'gate3_batch_comparison': comparison_package,
            'gate3_earned_candidate': earned_candidate,
            'gate3_completion_audit': completion_audit,
        }
        out_file = self.results_dir / f"gate3_report_{batch_name}.json"
        with open(out_file, 'w') as f:
            json.dump(out, f, indent=2, default=str)
        gate3_gate_completion = self.build_gate3_gate_completion_audit()
        out['gate3_gate_completion_audit'] = gate3_gate_completion.get('gate3_gate_completion_audit', {})
        with open(out_file, 'w') as f:
            json.dump(out, f, indent=2, default=str)
        return out


    def build_gate3_gate_completion_audit(self) -> Dict[str, Any]:
        """Build a gate-level Gate 3 completion audit across saved Gate 3 report surfaces."""
        return build_gate3_gate_completion_audit_from_project_root(project_root=self.results_dir.parent)


    def build_gate3_global_completion_report(self) -> Dict[str, Any]:
        """Build a Gate 3 global completion report that distinguishes capability from current saved-state completion."""
        return build_gate3_global_completion_report(project_root=self.results_dir.parent)


    def run_gate3_multi_route_completion_pass(self, batch_name: str, authored_summary: Dict[str, Any], validation_summary: Dict[str, Any], complete_cycle_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Run a normal saved-run multi-route Gate 3 completion pass."""
        batch_report = self.build_gate3_batch_report(batch_name, authored_summary)
        batch_summary = self.load_batch_summary(batch_name)
        real_capture_reference_surface = batch_report['gate3_batch_comparison']['gate3_batch_comparison']['real_capture_reference_surface']

        validation_route = build_gate3_saved_route_package(
            route_kind='validation',
            summary=validation_summary,
            authored_summary=authored_summary,
            real_capture_reference_surface=real_capture_reference_surface,
        )
        complete_route = build_gate3_saved_route_package(
            route_kind='complete_cycle',
            summary=complete_cycle_summary,
            authored_summary=authored_summary,
            real_capture_reference_surface=real_capture_reference_surface,
        )

        from evidence_validation_loop import EvidenceValidationLoop
        from complete_evidence_loop import CompleteEvidenceLoop

        validation_loop = EvidenceValidationLoop(output_dir=str(self.results_dir.parent / 'evidence_validation'))
        complete_loop = CompleteEvidenceLoop(output_dir=str(self.results_dir.parent / 'complete_evidence_loop'))

        validation_cycle_results = build_validation_cycle_results_from_route_package(route_package=validation_route)
        complete_cycle_results = build_complete_cycle_results_from_route_package(route_package=complete_route)

        validation_results_file = validation_loop.save_cycle_results(validation_cycle_results)
        complete_results_file = complete_loop.save_cycle_results(complete_cycle_results)
        gate3_gate_completion = self.build_gate3_gate_completion_audit()
        gate3_global_completion = self.build_gate3_global_completion_report()

        out = {
            'gate_3_status': 'IN_PROGRESS',
            'gate_clearance_authority': False,
            'report_scope': 'gate3_multi_route_completion_pass',
            'rules_version': 'AUREXIS_GATE_3_MULTI_ROUTE_COMPLETION_PASS_RULES_V1',
            'batch_name': batch_name,
            'batch_summary': batch_summary,
            'gate3_batch_report': batch_report.get('gate3_batch_report', {}),
            'gate3_validation_route': validation_route.get('gate_3_route_report', {}),
            'gate3_complete_cycle_route': complete_route.get('gate_3_route_report', {}),
            'gate3_gate_completion_audit': gate3_gate_completion.get('gate3_gate_completion_audit', {}),
            'gate3_global_completion_report': gate3_global_completion,
            'saved_results': {
                'batch_report_file': str(self.results_dir / f"gate3_report_{batch_name}.json"),
                'validation_results_file': validation_results_file,
                'complete_cycle_results_file': complete_results_file,
                'gate3_gate_completion_file': str(self.results_dir / 'gate3_gate_completion_audit.json'),
                'gate3_global_completion_file': str(self.results_dir / 'gate3_global_completion_report.json'),
            },
        }
        out_file = self.results_dir / f"gate3_multi_route_completion_{batch_name}.json"
        with open(out_file, 'w') as f:
            json.dump(out, f, indent=2, default=str)
        return out

    def run_gate3_canonical_saved_seed(self, batch_name: str) -> Dict[str, Any]:
        """Build the canonical saved multi-route Gate 3 state from one standard run."""
        batch_summary = self.load_batch_summary(batch_name)
        seed = build_gate3_canonical_saved_seed(batch_summary)
        multi_route = self.run_gate3_multi_route_completion_pass(
            batch_name,
            seed['authored_summary'],
            seed['validation_summary'],
            seed['complete_cycle_summary'],
        )
        gate3_global_completion = self.build_gate3_global_completion_report()
        out = {
            'report_scope': 'gate3_canonical_saved_seed',
            'rules_version': GATE_3_CANONICAL_SAVED_SEED_RULES_VERSION,
            'gate_3_status': 'IN_PROGRESS',
            'gate_clearance_authority': False,
            'batch_name': batch_name,
            'canonical_seed': seed,
            'gate3_multi_route_completion': multi_route,
            'gate3_global_completion_report': gate3_global_completion,
            'default_saved_state_complete': bool(gate3_global_completion.get('default_saved_state_complete', False)),
        }
        out_file = self.results_dir / f"gate3_canonical_seed_{batch_name}.json"
        with open(out_file, 'w') as f:
            json.dump(out, f, indent=2, default=str)
        out['saved_results'] = dict(multi_route.get('saved_results', {}))
        out['saved_results']['gate3_canonical_seed_file'] = str(out_file)
        return out


    def regenerate_gate3_packaged_default_state(self, batch_name: str) -> Dict[str, Any]:
        """Regenerate the packaged default Gate 3 saved state from one canonical run."""
        cleanup = clear_gate3_saved_outputs(project_root=self.results_dir.parent)
        canonical_seed = self.run_gate3_canonical_saved_seed(batch_name)
        final_report = build_gate3_final_completion_report(
            project_root=self.results_dir.parent,
            regenerated=True,
            regeneration_source=batch_name,
        )
        out = {
            'report_scope': 'gate3_packaged_default_state_regeneration',
            'rules_version': GATE_3_PACKAGED_DEFAULT_STATE_RULES_VERSION,
            'gate_3_status': 'IN_PROGRESS',
            'gate_clearance_authority': False,
            'batch_name': batch_name,
            'cleanup': cleanup,
            'gate3_canonical_saved_seed': canonical_seed,
            'gate3_final_completion_report': final_report,
            'default_saved_state_complete': bool(final_report.get('default_saved_state_complete', False)),
            'gate_3_complete_after_regeneration': bool(final_report.get('gate_3_complete_after_regeneration', False)),
        }
        out_file = self.results_dir / f"gate3_packaged_default_state_regeneration_{batch_name}.json"
        with open(out_file, 'w') as f:
            json.dump(out, f, indent=2, default=str)
        saved = dict(canonical_seed.get('saved_results', {}))
        saved['gate3_packaged_default_state_regeneration_file'] = str(out_file)
        saved['gate3_final_completion_report_file'] = str(self.results_dir / 'gate3_final_completion_report.json')
        out['saved_results'] = saved
        return out


    def run_gate3_default_pipeline(self, batch_name: str | None = None) -> Dict[str, Any]:
        """Run the default one-command Gate 3 packaged-state pipeline."""
        chosen_batch = batch_name
        if not chosen_batch:
            batches = self.list_available_batches()
            if not batches:
                raise FileNotFoundError('No evidence batches available for Gate 3 default pipeline')
            chosen_batch = batches[0]
        regeneration = self.regenerate_gate3_packaged_default_state(chosen_batch)
        final_report = dict(regeneration.get('gate3_final_completion_report', {}) or {})
        stamp = build_gate3_default_pipeline_stamp(
            project_root=self.results_dir.parent,
            batch_name=chosen_batch,
            regeneration_output=regeneration,
            final_completion_report=final_report,
        )
        out = {
            'report_scope': 'gate3_default_pipeline_run',
            'rules_version': GATE_3_DEFAULT_PIPELINE_RULES_VERSION,
            'gate_3_status': 'IN_PROGRESS',
            'gate_clearance_authority': False,
            'output_honesty_explicit': True,
            'batch_name': chosen_batch,
            'gate3_packaged_default_state_regeneration': regeneration,
            'gate3_final_completion_report': final_report,
            'gate3_default_pipeline_stamp': stamp,
            'default_saved_state_complete': bool(final_report.get('default_saved_state_complete', False)),
            'gate_3_complete_after_regeneration': bool(final_report.get('gate_3_complete_after_regeneration', False)),
        }
        out_file = self.results_dir / f"gate3_default_pipeline_run_{chosen_batch}.json"
        with open(out_file, 'w') as f:
            json.dump(out, f, indent=2, default=str)
        saved = dict(regeneration.get('saved_results', {}) or {})
        saved['gate3_default_pipeline_stamp_file'] = str(self.results_dir / 'gate3_default_pipeline_stamp.json')
        saved['gate3_default_pipeline_run_file'] = str(out_file)
        out['saved_results'] = saved
        return out


    def run_gate3_release_pipeline(self, batch_name: str | None = None) -> Dict[str, Any]:
        """Run the release/build-style Gate 3 pipeline and stamp the package root honestly."""
        default_run = self.run_gate3_default_pipeline(batch_name)
        chosen_batch = default_run.get('batch_name') or batch_name or ''
        final_report = dict(default_run.get('gate3_final_completion_report', {}) or {})
        root_stamp = build_gate3_root_package_completion_stamp(
            project_root=self.results_dir.parent,
            batch_name=chosen_batch,
            default_pipeline_output=default_run,
            final_completion_report=final_report,
        )
        out = {
            'report_scope': 'gate3_release_pipeline_run',
            'rules_version': GATE_3_RELEASE_PIPELINE_RULES_VERSION,
            'gate_3_status': 'IN_PROGRESS',
            'gate_clearance_authority': False,
            'output_honesty_explicit': True,
            'batch_name': chosen_batch,
            'gate3_default_pipeline_run': default_run,
            'gate3_root_package_completion_stamp': root_stamp,
            'package_precleared': bool(root_stamp.get('package_precleared', False)),
            'package_completion_state': root_stamp.get('package_completion_state', 'NOT_PRE_CLEARED'),
        }
        out_file = self.results_dir / f"gate3_release_pipeline_run_{chosen_batch}.json"
        with open(out_file, 'w') as f:
            json.dump(out, f, indent=2, default=str)
        saved = dict(default_run.get('saved_results', {}) or {})
        saved['gate3_root_package_completion_stamp_file'] = str(self.results_dir.parent / 'AUREXIS_GATE_3_PACKAGE_COMPLETION_STAMP.json')
        saved['gate3_release_pipeline_run_file'] = str(out_file)
        out['saved_results'] = saved
        return out

    def run_gate4_narrow_mobile_demo(self, batch_name: str | None = None) -> Dict[str, Any]:
        """Run the Gate 4 narrow mobile demo kickoff on top of the Gate 3 release pipeline."""
        chosen_batch = batch_name
        if not chosen_batch:
            batches = self.list_available_batches()
            if not batches:
                raise FileNotFoundError('No evidence batches available for Gate 4 narrow mobile demo')
            chosen_batch = batches[0]
        release_run = self.run_gate3_release_pipeline(chosen_batch)
        batch_summary = self.load_batch_summary(chosen_batch)
        demo_report = build_gate4_narrow_mobile_demo_report(
            project_root=self.results_dir.parent,
            batch_name=chosen_batch,
            release_pipeline_output=release_run,
            batch_summary=batch_summary,
        )
        out = {
            'report_scope': 'gate4_narrow_mobile_demo_run',
            'rules_version': GATE_4_NARROW_MOBILE_DEMO_RULES_VERSION,
            'gate_4_status': 'IN_PROGRESS',
            'gate_clearance_authority': False,
            'batch_name': chosen_batch,
            'gate3_release_pipeline_run': release_run,
            'gate4_narrow_mobile_demo_report': demo_report,
            'demonstration_ready': bool(demo_report.get('demonstration_ready', False)),
        }
        out_file = self.results_dir / f"gate4_narrow_mobile_demo_{chosen_batch}.json"
        with open(out_file, 'w') as f:
            json.dump(out, f, indent=2, default=str)
        saved = dict(release_run.get('saved_results', {}) or {})
        saved['gate4_narrow_mobile_demo_file'] = str(out_file)
        saved['gate4_root_mobile_demo_report_file'] = str(self.results_dir.parent / 'AUREXIS_GATE_4_NARROW_MOBILE_DEMO_REPORT.json')
        out['saved_results'] = saved
        return out


    def generate_batch_report(self, batch_name: str, authored_summary: Dict[str, Any] = None) -> str:
        """Generate comprehensive report for a batch"""
        quality_analysis = self.analyze_batch_quality(batch_name)
        eval_summary = self.run_batch_evaluation(batch_name)
        gate3_report = self.build_gate3_batch_report(batch_name, authored_summary) if authored_summary else None
        gate3_surface = gate3_report['gate3_batch_report'] if gate3_report else None
        
        report = f"""
# Evidence Batch Report: {batch_name}

## Overview
- Total Records: {quality_analysis['total_records']}
- Quality Score: {quality_analysis['quality_score']:.3f}
- Generated: {datetime.now().isoformat()}

## Confidence Analysis
- Mean Confidence: {quality_analysis['confidence_distribution'].get('mean', 0.0):.3f}
- High Confidence Ratio: {quality_analysis['confidence_distribution'].get('high_confidence_ratio', 0.0):.3f}
- Low Confidence Ratio: {quality_analysis['confidence_distribution'].get('low_confidence_ratio', 0.0):.3f}

## Primitive Analysis
- Average CV Primitives: {quality_analysis['primitive_analysis']['cv_primitives']['mean']:.1f}
- Average Segments: {quality_analysis['primitive_analysis']['segments']['mean']:.1f}
- Correlation: {quality_analysis['primitive_analysis']['correlation']:.3f}

## Temporal Analysis
- Duration: {quality_analysis['temporal_analysis'].get('duration_seconds', 0.0):.1f} seconds
- Capture Rate: {quality_analysis['temporal_analysis'].get('capture_rate', 0.0):.2f} FPS

## Processing Gaps
{chr(10).join('- ' + gap for gap in quality_analysis['processing_gaps']) if quality_analysis['processing_gaps'] else 'No significant gaps identified'}

## Evaluation Summary
- Average Score: {eval_summary.get('average_score', 0.0):.3f}
- Success Rate: {eval_summary.get('success_rate', 0.0):.3f}

## Gate 3 Batch Comparison
- Included: {bool(gate3_surface)}
- Comparison Ready: {gate3_surface.get('comparison_ready', False) if gate3_surface else False}
- Earned Candidate Ready: {gate3_surface.get('earned_candidate_ready', False) if gate3_surface else False}
- Earned Audit Ready: {gate3_surface.get('earned_audit_ready', False) if gate3_surface else False}
- Earned Promotion Passed: {gate3_surface.get('earned_promotion_passed', False) if gate3_surface else False}
- Promoted Evidence Tier: {gate3_surface.get('promoted_evidence_tier', 'N/A') if gate3_surface else 'N/A'}
- Blocking Reasons: {', '.join(gate3_surface.get('blocking_reasons', [])) if gate3_surface else 'N/A'}
- Completion Audit Passed: {gate3_report.get('gate3_completion_audit', {}).get('gate_3_complete', False) if gate3_report else False}
- Completion Audit Blocks: {', '.join(gate3_report.get('gate3_completion_audit', {}).get('blocking_components', [])) if gate3_report else 'N/A'}
- Gate-Level Audit Passed: {gate3_report.get('gate3_gate_completion_audit', {}).get('gate_3_complete', False) if gate3_report else False}
- Gate-Level Audit Blocks: {', '.join(gate3_report.get('gate3_gate_completion_audit', {}).get('blocking_components', [])) if gate3_report else 'N/A'}

## Recommendations
{self._generate_recommendations(quality_analysis, eval_summary)}
        """
        
        # Save report
        report_file = self.results_dir / f"report_{batch_name}.md"
        with open(report_file, 'w') as f:
            f.write(report)
        
        return str(report_file)
    
    def _generate_recommendations(self, quality_analysis: Dict[str, Any], eval_summary: Dict[str, Any]) -> str:
        """Generate recommendations based on analysis"""
        recommendations = []
        
        # Quality-based recommendations
        if quality_analysis['quality_score'] < 0.5:
            recommendations.append("- Consider improving lighting conditions")
            recommendations.append("- Check camera focus and positioning")
        
        # Confidence-based recommendations
        conf_dist = quality_analysis['confidence_distribution']
        if conf_dist.get('low_confidence_ratio', 0) > 0.3:
            recommendations.append("- High proportion of low-confidence detections - consider scene complexity")
        
        # Primitive-based recommendations
        prim_analysis = quality_analysis['primitive_analysis']
        if prim_analysis['cv_primitives']['mean'] < 5:
            recommendations.append("- Low primitive detection - ensure sufficient visual content")
        
        if not recommendations:
            recommendations.append("- Batch quality looks good - proceed with training data generation")
        
        return '\n'.join(recommendations)


def process_all_available_batches():
    """Process all available evidence batches"""
    processor = EvidenceBatchProcessor()
    batches = processor.list_available_batches()
    
    print(f"Found {len(batches)} batches to process")
    
    for batch in batches:
        print(f"\nProcessing batch: {batch}")
        
        try:
            # Generate quality analysis
            quality = processor.analyze_batch_quality(batch)
            print(f"Quality score: {quality['quality_score']:.3f}")
            
            # Generate training data
            training_path = processor.process_batch_to_training_data(batch)
            print(f"Training data: {training_path}")
            
            # Generate report
            report_path = processor.generate_batch_report(batch)
            print(f"Report: {report_path}")
            
        except Exception as e:
            print(f"Error processing batch {batch}: {e}")


if __name__ == "__main__":
    process_all_available_batches()
