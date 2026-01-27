"""
Driver Manifest Builder Module for VRP Solver

This module generates driver manifests in CSV and PDF formats with
stop-by-stop delivery instructions and special handling requirements.
"""

import csv
import io
from typing import List, Dict, Any
from dashboard.csv_parser import Package, Destination
from dashboard.financial_engine import RouteCost
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT


class ManifestBuilder:
    """Generates driver manifests in CSV and PDF formats."""
    
    def _format_special_handling(self, package: Package) -> str:
        """
        Format special handling requirements for a package.
        
        Args:
            package: Package object with constraint flags
            
        Returns:
            String with special handling icons/text
        """
        handling = []
        
        if package.fragile:
            handling.append("⚠️ FRAGILE")
        
        if package.this_side_up:
            handling.append("⬆️ THIS SIDE UP")
        
        return ", ".join(handling) if handling else ""
    
    def generate_csv(self, route: List[int], packages: List[Package], 
                    destinations: List[Destination]) -> str:
        """
        Generate CSV manifest with stop-by-stop delivery instructions.
        
        Args:
            route: List of customer IDs in route order (0 is depot)
            packages: List of all Package objects
            destinations: List of Destination objects
            
        Returns:
            CSV content as string
        """
        # Create destination lookup
        dest_map = {dest.name: dest for dest in destinations}
        
        # Build CSV data
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Stop',
            'Source Name',
            'Destination Name',
            'Order ID',
            'Dimensions',
            'Weight (kg)',
            'Special Handling'
        ])
        
        # Process each stop in route (skip depot at index 0)
        stop_number = 1
        for customer_id in route[1:]:  # Skip depot
            # Find destination for this customer
            destination = None
            for dest in destinations:
                if dest.name == f"Customer {customer_id}":
                    destination = dest
                    break
            
            # If no destination found, try matching by index
            if destination is None and customer_id <= len(destinations):
                destination = destinations[customer_id - 1]
            
            if destination:
                # Write row for each package at this destination
                for package in destination.packages:
                    # Default source name to "Depot" if missing or empty
                    source_name = package.source_name
                    if not source_name or source_name.strip() == '' or str(source_name).lower() == 'nan':
                        source_name = "Depot"
                    
                    # Format dimensions as "LxWxH cm"
                    dimensions = f"{package.length_m * 100:.1f}x{package.width_m * 100:.1f}x{package.height_m * 100:.1f} cm"
                    
                    # Get special handling
                    special_handling = self._format_special_handling(package)
                    
                    writer.writerow([
                        stop_number,
                        source_name,
                        package.destination_name,
                        package.order_id,
                        dimensions,
                        f"{package.weight_kg:.2f}",
                        special_handling
                    ])
            
            stop_number += 1
        
        return output.getvalue()
    
    def generate_pdf(self, route: List[int], packages: List[Package],
                    destinations: List[Destination], 
                    vehicle_name: str, route_cost: RouteCost) -> bytes:
        """
        Generate PDF manifest with comprehensive delivery instructions.
        
        Args:
            route: List of customer IDs in route order (0 is depot)
            packages: List of all Package objects
            destinations: List of Destination objects
            vehicle_name: Name of the assigned vehicle
            route_cost: RouteCost object with financial details
            
        Returns:
            PDF content as bytes
        """
        # Create PDF buffer
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                               topMargin=0.5*inch, bottomMargin=0.5*inch,
                               leftMargin=0.5*inch, rightMargin=0.5*inch)
        
        # Container for PDF elements
        elements = []
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=12,
            alignment=TA_CENTER
        )
        
        header_style = ParagraphStyle(
            'CustomHeader',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#2c5aa0'),
            spaceAfter=6
        )
        
        # Title
        title = Paragraph("Driver Delivery Manifest", title_style)
        elements.append(title)
        elements.append(Spacer(1, 0.2*inch))
        
        # Header information
        header_data = [
            ['Vehicle:', vehicle_name, 'Route ID:', str(route_cost.route_id)],
            ['Distance:', f"{route_cost.distance_km:.2f} km", 'Time:', f"{route_cost.time_hours:.2f} hours"],
            ['Fuel Used:', f"{route_cost.fuel_consumed_L:.2f} L", 'Total Cost:', f"${route_cost.total_cost:.2f}"]
        ]
        
        header_table = Table(header_data, colWidths=[1.2*inch, 2*inch, 1.2*inch, 2*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8f0f8')),
            ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#e8f0f8')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(header_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Delivery instructions header
        instructions_header = Paragraph("Delivery Instructions", header_style)
        elements.append(instructions_header)
        elements.append(Spacer(1, 0.1*inch))
        
        # Build delivery table
        table_data = [
            ['Stop', 'Source', 'Destination', 'Order ID', 'Dimensions', 'Weight', 'Special']
        ]
        
        # Create destination lookup
        dest_map = {dest.name: dest for dest in destinations}
        
        # Process each stop in route (skip depot at index 0)
        stop_number = 1
        total_packages = 0
        total_weight = 0.0
        
        for customer_id in route[1:]:  # Skip depot
            # Find destination for this customer
            destination = None
            for dest in destinations:
                if dest.name == f"Customer {customer_id}":
                    destination = dest
                    break
            
            # If no destination found, try matching by index
            if destination is None and customer_id <= len(destinations):
                destination = destinations[customer_id - 1]
            
            if destination:
                # Add row for each package at this destination
                for package in destination.packages:
                    # Default source name to "Depot" if missing or empty
                    source_name = package.source_name
                    if not source_name or source_name.strip() == '' or str(source_name).lower() == 'nan':
                        source_name = "Depot"
                    
                    # Format dimensions as "LxWxH cm"
                    dimensions = f"{package.length_m * 100:.0f}x{package.width_m * 100:.0f}x{package.height_m * 100:.0f}"
                    
                    # Get special handling
                    special_handling = self._format_special_handling(package)
                    
                    table_data.append([
                        str(stop_number),
                        source_name,
                        package.destination_name,
                        package.order_id,
                        dimensions,
                        f"{package.weight_kg:.1f}",
                        special_handling
                    ])
                    
                    total_packages += 1
                    total_weight += package.weight_kg
            
            stop_number += 1
        
        # Create table
        delivery_table = Table(table_data, colWidths=[0.5*inch, 1.2*inch, 1.2*inch, 0.9*inch, 1*inch, 0.7*inch, 1.5*inch])
        delivery_table.setStyle(TableStyle([
            # Header row styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5aa0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            
            # Data rows styling
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Stop number centered
            ('ALIGN', (4, 1), (5, -1), 'CENTER'),  # Dimensions and weight centered
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ]))
        
        elements.append(delivery_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Footer with summary statistics
        summary_data = [
            ['Summary Statistics'],
            ['Total Stops:', str(len(route) - 1)],
            ['Total Packages:', str(total_packages)],
            ['Total Weight:', f"{total_weight:.2f} kg"],
            ['Fuel Efficiency:', f"{route_cost.fuel_efficiency_km_per_L:.2f} km/L"],
        ]
        
        summary_table = Table(summary_data, colWidths=[2*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5aa0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('SPAN', (0, 0), (-1, 0)),
            
            ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#e8f0f8')),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(summary_table)
        
        # Build PDF
        doc.build(elements)
        
        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
